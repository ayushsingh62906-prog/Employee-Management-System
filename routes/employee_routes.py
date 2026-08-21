# ==========================================================
# FILE : routes/employee_routes.py
# PURPOSE : Admin - Employee Management Module
#           Add / View / Edit / Search & Filter /
#           Soft Delete / Restore / Permanent Delete
# ==========================================================

import os
from datetime import datetime

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

# Photo file ka naam safe banane ke liye
# (agar user photo ka naam "../../etc/passwd.png" jaisa
# kuch rakh de to ye function usko saaf kar deta hai)
from werkzeug.utils import secure_filename

# db.py se "employees" collection import kar rahe hain
from db import employees, departments

# Pichle step me banaya hua decorator import kar rahe hain
from utils.decorators import role_required


# ==========================================================
# BLUEPRINT SETUP
#
# Blueprint = ek mini Flask app jiske apne routes hote hain
# "employees" -> is Blueprint ka naam (isi naam se
#                url_for('employees.list_employees') likhenge)
# url_prefix  -> is Blueprint ke andar jo bhi route banega
#                uske URL ke shuru me automatically
#                "/admin/employees" lag jayega
# ==========================================================

employee_bp = Blueprint(
    "employees",
    __name__,
    url_prefix="/admin/employees"
)


# Photo upload me sirf ye extensions allow karenge
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Photos kaha save hongi uska absolute path bana rahe hain
# __file__            -> is file (employee_routes.py) ka path
# os.path.dirname     -> uska folder (routes/)
# ".."                -> ek level upar (project root)
# phir static/uploads/employees tak jaate hain
UPLOAD_FOLDER = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "static", "uploads", "employees"
)


def allowed_file(filename):
    # filename me "." hai (extension separate karne ke liye)
    # AND extension allowed list me hai
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ==========================================================
# HELPER FUNCTION : NEXT EMPLOYEE ID GENERATE KARNA
# Format : EMP0001, EMP0002 ...
# ==========================================================

def generate_employee_id():

    # MongoDB se sabse aakhri (latest) insert hua employee
    # nikal rahe hain -> sort by _id descending (-1),
    # find_one isliye ek hi document milega
    last_employee = employees.find_one(
        sort=[("_id", -1)]
    )

    # Agar koi employee hi nahi hai database me
    # to pehla ID "EMP0001" se start karo
    if not last_employee or "employee_id" not in last_employee:
        return "EMP0001"

    # "EMP0007" me se "EMP" hata ke "0007" -> int -> 7
    last_number = int(last_employee["employee_id"].replace("EMP", ""))

    new_number = last_number + 1

    # :04d ka matlab -> number ko 4 digit ka bana do,
    # aage 0 laga ke. Jaise 8 -> "0008"
    return f"EMP{new_number:04d}"


# ==========================================================
# ROUTE 1 : EMPLOYEE LIST (Search & Filter yahi se hota hai)
# URL : GET /admin/employees/
# ==========================================================

@employee_bp.route("/")
@role_required("admin")   # sirf admin access kar sakta hai
def list_employees():

    # -----------------------------
    # Browser URL se query params nikal rahe hain
    # jaise: /admin/employees/?q=rahul&department=IT
    # -----------------------------
    search_query = request.args.get("q", "").strip()
    department_filter = request.args.get("department", "")
    status_filter = request.args.get("status", "")

    # trash=1 hoga to deleted employees dikhayenge,
    # warna normal active list
    show_deleted = request.args.get("trash", "0") == "1"

    # -----------------------------
    # MongoDB "query" dictionary step by step bana rahe hain
    # -----------------------------

    # Agar trash dekhna hai to sirf wahi jinka is_deleted True hai
    # warna wo jinka is_deleted True NAHI hai ($ne = not equal)
    query = {"is_deleted": True} if show_deleted else {"is_deleted": {"$ne": True}}

    # Agar search box me kuch type kiya hai
    if search_query:
        # $or -> in me se koi ek bhi field match ho jaye to result aayega
        # $regex -> jaise text ke andar partial match dhundhna
        #           (SQL ke LIKE '%text%' jaisa)
        # $options: "i" -> case-insensitive (Rahul / rahul dono chalega)
        query["$or"] = [
            {"full_name": {"$regex": search_query, "$options": "i"}},
            {"email": {"$regex": search_query, "$options": "i"}},
            {"employee_id": {"$regex": search_query, "$options": "i"}},
            {"phone": {"$regex": search_query, "$options": "i"}},
        ]

    # Agar department dropdown se koi department select kiya hai
    if department_filter:
        query["department"] = department_filter

    # Status filter sirf tab lagega jab trash na dekh rahe ho
    if status_filter and not show_deleted:
        query["status"] = status_filter

    # -----------------------------
    # Ab final query MongoDB me chalao
    # find(query) -> matching sab documents
    # .sort("created_at", -1) -> naye employees sabse upar
    # list(...) -> MongoDB cursor ko Python list me convert
    # -----------------------------
    employee_list = list(employees.find(query).sort("created_at", -1))

    # -----------------------------
    # Department dropdown ke liye distinct (unique)
    # department names nikal rahe hain existing employees se
    # -----------------------------
    departments_list = employees.distinct("department", {"is_deleted": {"$ne": True}})
    departments_list = [d for d in departments_list if d]  # khali values hata do

    # -----------------------------
    # Template ko sab data bhej rahe hain
    # -----------------------------
    return render_template(
        "admin/employees/list.html",
        employees=employee_list,
        departments_list=departments_list,
        search_query=search_query,
        department_filter=department_filter,
        status_filter=status_filter,
        show_deleted=show_deleted,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : ADD EMPLOYEE
# URL : GET (form dikhana) / POST (form submit karna)
# ==========================================================

@employee_bp.route("/add", methods=["GET", "POST"])
@role_required("admin")
def add_employee():

    # Agar form submit hua hai (Save button dabaya)
    if request.method == "POST":

        # -----------------------------
        # Form se saara data nikal rahe hain
        # -----------------------------
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender", "")
        dob = request.form.get("dob", "")
        department = request.form.get("department", "").strip()
        designation = request.form.get("designation", "").strip()
        employee_type = request.form.get("employee_type", "Full-time")
        date_of_joining = request.form.get("date_of_joining", "")
        salary = request.form.get("salary", "0")
        address = request.form.get("address", "").strip()

        # -----------------------------
        # Basic Validation
        # -----------------------------
        if not full_name or not email or not department or not designation:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("employees.add_employee"))

        # Same email se pehle se koi active employee hai kya?
        if employees.find_one({"email": email, "is_deleted": {"$ne": True}}):
            flash("An employee with this email already exists.", "danger")
            return redirect(url_for("employees.add_employee"))

        # -----------------------------
        # Profile Photo Upload (optional)
        # -----------------------------
        photo_filename = None
        photo = request.files.get("photo")

        if photo and photo.filename and allowed_file(photo.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = photo.filename.rsplit(".", 1)[1].lower()
            photo_filename = secure_filename(
                f"{email.split('@')[0]}_{int(datetime.utcnow().timestamp())}.{ext}"
            )
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

        # -----------------------------
        # Employee ID generate karna
        # -----------------------------
        new_emp_id = generate_employee_id()

        # -----------------------------
        # 1. Employees collection me record insert
        # -----------------------------
        employees.insert_one({
            "employee_id": new_emp_id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "gender": gender,
            "dob": dob,
            "department": department,
            "designation": designation,
            "employee_type": employee_type,
            "date_of_joining": date_of_joining,
            "salary": float(salary) if salary else 0,
            "address": address,
            "photo": photo_filename,
            "status": "Active",
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        # -----------------------------
        # 2. Users collection me bhi entry banana
        #    taaki employee baad me password set karke login kar sake
        # -----------------------------
        from db import users   # users collection

        # Check karo same email se user already to nahi hai
        if not users.find_one({"email": email}):
            users.insert_one({
                "username": full_name,           # display name
                "email": email,
                "employee_id": new_emp_id,       # important link
                "password": None,                # abhi password set nahi hai
                "role": "employee",
                "password_set": False,           # flag
                "created_at": datetime.utcnow(),
            })

        flash(f"Employee '{full_name}' added successfully. Emp ID: {new_emp_id}", "success")
        return redirect(url_for("employees.list_employees"))

    # ========== GET request -> form dikhana ==========
    # Admin ne jo departments add kiye, wahi list
    dept_docs = list(departments.find(
        {"is_deleted": {"$ne": True}, "status": "Active"}
    ).sort("name", 1))
    departments_list = [d.get("name") for d in dept_docs if d.get("name")]

    DESIGNATION_MAP = {
        "Engineering": ["Software Engineer", "Senior Developer", "Team Lead", "QA Engineer"],
        "IT": ["Software Engineer", "System Admin", "Support Engineer", "DevOps Engineer"],
        "Sales": ["Sales Executive", "Sales Manager", "Account Manager"],
        "Marketing": ["Marketing Executive", "Content Writer", "Digital Marketer"],
        "Customer Support": ["Support Executive", "Support Lead", "Customer Success"],
        "HR": ["HR Executive", "HR Manager", "Recruiter"],
        "Finance": ["Accountant", "Finance Executive", "Finance Manager"],
    }

    return render_template(
        "admin/employees/add.html",
        departments_list=departments_list,
        designation_map=DESIGNATION_MAP,
        username=session["username"],
        role=session["role"],
    )

   
# ==========================================================
# ROUTE 3 : EDIT EMPLOYEE
# URL : /admin/employees/edit/<employee_id>
# <employee_id> -> URL ka dynamic part, jaise
#                  /admin/employees/edit/EMP0003
# ==========================================================

@employee_bp.route("/edit/<employee_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_employee(employee_id):

    # Pehle us employee ko dhundo jiska ID URL me aaya hai
    employee = employees.find_one({"employee_id": employee_id})

    # Agar wo employee exist hi nahi karta (galat ID)
    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for("employees.list_employees"))

    # Agar Edit form submit hua hai
    if request.method == "POST":

        # Update karne wala data ek dictionary me taiyar kar rahe hain
        update_data = {
            "full_name": request.form.get("full_name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "gender": request.form.get("gender", ""),
            "dob": request.form.get("dob", ""),
            "department": request.form.get("department", "").strip(),
            "designation": request.form.get("designation", "").strip(),
            "employee_type": request.form.get("employee_type", "Full-time"),
            "date_of_joining": request.form.get("date_of_joining", ""),
            "salary": float(request.form.get("salary") or 0),
            "address": request.form.get("address", "").strip(),
            "status": request.form.get("status", "Active"),
            "updated_at": datetime.utcnow(),
        }

        # -----------------------------
        # Agar edit form me nayi photo upload hui hai
        # to purani photo ki jagah nayi save karo
        # -----------------------------
        photo = request.files.get("photo")

        if photo and photo.filename and allowed_file(photo.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = photo.filename.rsplit(".", 1)[1].lower()
            photo_filename = secure_filename(
                f"{employee_id}_{int(datetime.utcnow().timestamp())}.{ext}"
            )
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))
            update_data["photo"] = photo_filename

        # -----------------------------
        # MongoDB me update_one() se document update karna
        # $set -> sirf diye gaye fields update honge,
        #         baaki document waisa hi rahega
        # -----------------------------
        employees.update_one(
            {"employee_id": employee_id},
            {"$set": update_data}
        )

        flash("Employee details updated successfully.", "success")
        return redirect(url_for("employees.view_employee", employee_id=employee_id))

    # -----------------------------
    # GET request -> edit form dikhana, existing data ke saath
    # -----------------------------
    departments_list = employees.distinct("department", {"is_deleted": {"$ne": True}})
    departments_list = [d for d in departments_list if d]

    return render_template(
        "admin/employees/edit.html",
        employee=employee,
        departments_list=departments_list,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 4 : VIEW EMPLOYEE PROFILE
# URL : /admin/employees/view/<employee_id>
# ==========================================================

@employee_bp.route("/view/<employee_id>")
@role_required("admin")
def view_employee(employee_id):

    employee = employees.find_one({"employee_id": employee_id})

    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for("employees.list_employees"))

    return render_template(
        "admin/employees/profile.html",
        employee=employee,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 5 : SOFT DELETE
# Employee list se hata do, lekin database me record rahega
# URL : POST /admin/employees/delete/<employee_id>
# ==========================================================

@employee_bp.route("/delete/<employee_id>", methods=["POST"])
@role_required("admin")
def soft_delete_employee(employee_id):

    # Sirf ek flag update kar rahe hain, document delete nahi ho raha
    employees.update_one(
        {"employee_id": employee_id},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )

    flash("Employee moved to Trash.", "success")
    return redirect(url_for("employees.list_employees"))


# ==========================================================
# ROUTE 6 : RESTORE
# Trash se wapas active list me le aana
# URL : POST /admin/employees/restore/<employee_id>
# ==========================================================

@employee_bp.route("/restore/<employee_id>", methods=["POST"])
@role_required("admin")
def restore_employee(employee_id):

    employees.update_one(
        {"employee_id": employee_id},
        {"$set": {"is_deleted": False, "updated_at": datetime.utcnow()}}
    )

    flash("Employee restored successfully.", "success")
    # trash=1 isliye taaki restore karne ke baad trash page pe hi rahe
    return redirect(url_for("employees.list_employees", trash=1))


# ==========================================================
# ROUTE 7 : PERMANENT DELETE
# Database se hamesha ke liye delete, wapas nahi aa sakta
# URL : POST /admin/employees/delete-permanent/<employee_id>
# ==========================================================

@employee_bp.route("/delete-permanent/<employee_id>", methods=["POST"])
@role_required("admin")
def permanent_delete_employee(employee_id):

    # delete_one() -> is baar sach me document DB se hata diya
    employees.delete_one({"employee_id": employee_id})

    flash("Employee permanently deleted.", "success")
    return redirect(url_for("employees.list_employees", trash=1))


# ==========================================================
# ROUTE 8 (BONUS) : QUICK STATUS TOGGLE (Active <-> Inactive)
# Isko abhi UI me use nahi kiya, lekin future me kaam aayega
# jaise ek button se sidha Active/Inactive switch karna ho
# ==========================================================

@employee_bp.route("/toggle-status/<employee_id>", methods=["POST"])
@role_required("admin")
def toggle_status(employee_id):

    employee = employees.find_one({"employee_id": employee_id})

    if employee:
        # Agar abhi Active hai to Inactive kar do, warna Active kar do
        new_status = "Inactive" if employee.get("status") == "Active" else "Active"

        employees.update_one(
            {"employee_id": employee_id},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
        )

        flash(f"Employee marked as {new_status}.", "success")

    return redirect(url_for("employees.list_employees"))