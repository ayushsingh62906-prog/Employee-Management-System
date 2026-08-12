# Flask ke required modules import kar rahe hain
from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from datetime import datetime
# Password ko securely hash aur verify karne ke liye
from werkzeug.security import generate_password_hash, check_password_hash

# db.py se MongoDB ki users collection import kar rahe hain
from db import *


# Flask application create karna
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))



# ============================================================
# Project root (BASE_DIR) ko sys.path me daal rahe hain taaki
# "routes/" aur "utils/" folders ko top-level packages ki tarah
# import kar saken (e.g. from routes.employee_routes import ...)
#
# Kyu chahiye: app.py "backend/" folder ke andar hai, aur
# "routes/", "utils/" folder uske BAHAR (project root me) hain.
# Python by default sirf apne khud ke folder me imports dhundta
# hai, isliye humein manually BASE_DIR ko sys.path me add karna
# padta hai taaki "from routes.employee_routes import ..." chale.
# ============================================================
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Naya Blueprint import kar rahe hain
from routes.employee_routes import employee_bp
from routes.department_routes import department_bp
from routes.attendance_routes import attendance_bp
from routes.employee_attendance_routes import employee_attendance_bp
from routes.leave_routes import leave_bp
from routes.employee_leave_routes import employee_leave_bp
from routes.payroll_routes import payroll_bp
from routes.announcement_routes import announcement_bp
from routes.settings_routes import settings_bp
from routes.employee_payroll_routes import employee_payroll_bp
from routes.job_routes import job_bp
from routes.exit_routes import exit_bp
from routes.employee_exit_routes import employee_exit_bp
from routes.exam_routes import exam_bp
from routes.onboarding_routes import onboarding_bp

# Pichle steps me banaya decorator import kar rahe hain
from utils.decorators import login_required, role_required





app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# Flash messages aur session ke liye secret key
app.secret_key = "my_secret_key"

# ============================================================
# Blueprints Register Karna
#
# Isse Flask ko pata chalta hai ki employee_routes.py me
# jo bhi routes likhe hain (add/edit/delete/view/list),
# unhe bhi is app ka hi hissa maan lo
# ============================================================
app.register_blueprint(employee_bp)
app.register_blueprint(department_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(employee_attendance_bp)
app.register_blueprint(leave_bp)
app.register_blueprint(employee_leave_bp)
app.register_blueprint(payroll_bp)
app.register_blueprint(announcement_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(employee_payroll_bp)
app.register_blueprint(job_bp)
app.register_blueprint(exit_bp)
app.register_blueprint(employee_exit_bp)
app.register_blueprint(exam_bp)
app.register_blueprint(onboarding_bp)

# =====================================================
# HOME ROUTE
# =====================================================

# =====================================================
# PUBLIC HOME PAGE
# Website khulte hi yeh page aayega
# Announcements + Job Openings + Login button
# =====================================================

@app.route("/")
def home():

    # Latest announcements nikalna (sirf type = announcement)
    announcements = list(notifications.find(
        {"type": "announcement"}
    ).sort("created_at", -1).limit(6))

    # Job openings abhi ke liye empty list
    # (baad me HR module se real data aayega)
    job_openings = list(recruitment.find(
        {"type": "job", "status": "Open"}
    ).sort("created_at", -1).limit(6))

    return render_template(
        "public/home.html",
        announcements=announcements,
        job_openings=job_openings
    )

# =====================================================
# REGISTER ROUTE
# =====================================================

# Ye route GET aur POST dono request accept karega
@app.route("/register", methods=["GET", "POST"])
def register():

    # Agar Register button press hua
    if request.method == "POST":

        # HTML form se values lena
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        # Role ko lowercase me save karna
        role = request.form["role"].lower()

        # ------------------------------------------
        # Check karo email pehle se database me hai ya nahi
        # ------------------------------------------

        existing_user = users.find_one({"email": email})

        if existing_user:
            flash("Email already exists", "error")
            return redirect(url_for("register"))

        # ------------------------------------------
        # Password ko Hash karna
        # Plain password kabhi database me store nahi karte
        # ------------------------------------------

        hashed_password = generate_password_hash(password)

        # ------------------------------------------
        # MongoDB me user save karna
        # insert_one() ek document save karta hai
        # ------------------------------------------

        users.insert_one({

            "username": username,

            "email": email,

            "password": hashed_password,

            "role": role

        })

        flash("Registration Successful. Please Login.", "success")

        return redirect(url_for("login"))

    # Agar GET request hai to Register page open karo
    return render_template("autho/register.html")

# ==========================================
# LOGIN ROUTE
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Agar user form submit karta hai
    if request.method == "POST":

        # Form se data lena
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        # Database me user search karna
        user = users.find_one({"email": email})

        # Agar user exist karta hai aur password sahi hai
        if user and check_password_hash(user["password"], password):

            # -----------------------------
            # SESSION CREATE
            # -----------------------------
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            flash(f"Welcome {user['username']}!", "success")

            # -----------------------------
            # ROLE BASED REDIRECTION
            # -----------------------------
            # Role ko lowercase me convert karna
            role = session["role"].lower()

            if role == "admin":
              return redirect(url_for("admin_dashboard"))

            elif role == "hr":
              return redirect(url_for("hr_dashboard"))

            elif role == "employee":
              return redirect(url_for("employee_dashboard"))

           # Agar role invalid ho
            flash("Invalid User Role", "danger")
            return redirect(url_for("login"))

        # Agar password ya email galat ho
        else:
            flash("Invalid Email or Password", "danger")

    # Login page open karna
    return render_template("autho/login.html")



# =====================================================
# SET PASSWORD (Employee first time password set kare)
# URL : /set-password
# Emp ID + Email + New Password se password set hoga
# =====================================================

@app.route("/set-password", methods=["GET", "POST"])
def set_password():

    if request.method == "POST":

        emp_id = request.form.get("employee_id", "").strip().upper()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Basic validation
        if not emp_id or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("set_password"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("set_password"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("set_password"))

        # User dhundo (employee_id + email se)
        user = users.find_one({
            "employee_id": emp_id,
            "email": email,
            "role": "employee"
        })

        if not user:
            flash("Invalid Employee ID or Email.", "danger")
            return redirect(url_for("set_password"))

        # Agar password pehle se set hai to
        if user.get("password_set"):
            flash("Password already set. Please login.", "warning")
            return redirect(url_for("login"))

        # Password hash karke save karo
        hashed = generate_password_hash(password)

        users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "password": hashed,
                "password_set": True,
                "updated_at": datetime.utcnow()
            }}
        )

        flash("Password set successfully! You can now login.", "success")
        return redirect(url_for("login"))

    # GET request
    return render_template("autho/set_password.html")
# =====================================================
# DASHBOARD
# =====================================================

# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():

    # -----------------------------
    # Dashboard Statistics
    # -----------------------------
    employee_count = employees.count_documents({"is_deleted": {"$ne": True}})
    department_count = departments.count_documents({"is_deleted": {"$ne": True}})
    attendance_count = attendance.count_documents({})          # baad me filter laga denge
    leave_count = leave_requests.count_documents({"status": "Pending"})
   
    
    

    # -----------------------------
    # Recent Activities (simple version)
    # Last 5 employees + last 3 departments
    # -----------------------------
    recent_activities = []

    # Recent employees
    recent_emps = list(employees.find(
        {"is_deleted": {"$ne": True}}
    ).sort("created_at", -1).limit(4))

    for emp in recent_emps:
        recent_activities.append({
            "message": f"New employee added: {emp.get('full_name', 'Unknown')} ({emp.get('employee_id')})",
            "time": emp.get("created_at").strftime("%d %b, %I:%M %p") if emp.get("created_at") else "-"
        })

    # Recent departments
    recent_depts = list(departments.find(
        {"is_deleted": {"$ne": True}}
    ).sort("created_at", -1).limit(3))

    for dept in recent_depts:
        recent_activities.append({
            "message": f"New department created: {dept.get('name')} ({dept.get('department_id')})",
            "time": dept.get("created_at").strftime("%d %b, %I:%M %p") if dept.get("created_at") else "-"
        })

    # Sort by time (optional - simple list is fine for now)
    recent_activities = recent_activities[:7]   # max 7 dikhayenge

    return render_template(
        "admin/dashboard.html",
        username=session["username"],
        email=session["email"],
        role=session["role"],
        employee_count=employee_count,
        department_count=department_count,
        attendance_count=attendance_count,
        leave_count=leave_count,
        recent_activities=recent_activities
   
    )
    
    
    # =====================================================
# HR DASHBOARD
# =====================================================

@app.route("/hr/dashboard")
@role_required("hr")
def hr_dashboard():

    # -----------------------------
    # Dashboard Statistics
    # -----------------------------
    open_jobs_count = recruitment.count_documents({
        "type": "job",
        "status": "Open"
    })

    new_applications_count = recruitment.count_documents({
        "type": "application",
        "status": "Applied"
    })

    pending_resignations_count = recruitment.count_documents({
        "type": "resignation",
        "status": "Pending"
    })

    total_employees_count = employees.count_documents({
        "is_deleted": {"$ne": True}
    })

    return render_template(
        "hr/dashboard.html",
        username=session["username"],
        role=session["role"],
        open_jobs_count=open_jobs_count,
        new_applications_count=new_applications_count,
        pending_resignations_count=pending_resignations_count,
        total_employees_count=total_employees_count,
    )

# =====================================================
# EMPLOYEE DASHBOARD
# =====================================================

@app.route("/employee/dashboard")
@role_required("employee")
def employee_dashboard():

    emp = employees.find_one({
        "email": session.get("email"),
        "is_deleted": {"$ne": True}
    })

    today_record = None
    pending_leaves = 0
    latest_payslip = None
    days_present = 0

    if emp:

        today = datetime.now().strftime("%Y-%m-%d")
        current_month = datetime.now().strftime("%Y-%m")

        # Aaj check-in hua ya nahi
        today_record = attendance.find_one({
            "employee_id": emp["employee_id"],
            "date": today
        })

        # Pending leave requests count
        pending_leaves = leave_requests.count_documents({
            "employee_id": emp["employee_id"],
            "status": "Pending"
        })

        # Is mahine kitne din present rahe (Present + Half Day + Late sab count)
        days_present = attendance.count_documents({
            "employee_id": emp["employee_id"],
            "date": {"$regex": f"^{current_month}"},
            "status": {"$in": ["Present", "Half Day", "Late"]}
        })

        # Sabse latest payslip
        latest_payslip = salary.find_one(
            {"employee_id": emp["employee_id"]},
            sort=[("created_at", -1)]
        )

    return render_template(
        "employee/dashboard.html",
        employee=emp,
        today_record=today_record,
        pending_leaves=pending_leaves,
        days_present=days_present,
        latest_payslip=latest_payslip,
        username=session["username"],
        role=session["role"],
    )
# =====================================================
# LOGOUT ROUTE
# =====================================================


# Logout Route
@app.route("/logout")
def logout():

    # Session ki saari information delete kar do
    session.clear()

    # Success message
    flash("Logged out successfully.", "success")

    # Login page par redirect
    return redirect(url_for("login"))

# =====================================================
# APPLICATION START
# =====================================================

# Ye line app ko start karti hai

if __name__ == "__main__":

    app.run(debug=True)