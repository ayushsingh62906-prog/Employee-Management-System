# ==========================================================
# FILE : routes/department_routes.py
# PURPOSE : Admin - Department Management Module
#           Add / View / Edit / Search & Filter /
#           Soft Delete / Restore / Permanent Delete
# ==========================================================

from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

# db.py se departments collection import
from db import departments, employees

# Role based access control ke liye decorator
from utils.decorators import role_required


# ==========================================================
# BLUEPRINT SETUP
# "departments" naam se blueprint
# URL prefix -> /admin/departments
# ==========================================================

department_bp = Blueprint(
    "departments",
    __name__,
    url_prefix="/admin/departments"
)


# ==========================================================
# HELPER : Next Department ID generate karna
# Format : DEPT0001, DEPT0002 ...
# ==========================================================

def generate_department_id():
    # Sabse latest department nikalne ke liye _id descending sort
    last_dept = departments.find_one(sort=[("_id", -1)])

    # Agar koi department hi nahi hai to pehla ID
    if not last_dept or "department_id" not in last_dept:
        return "DEPT0001"

    # "DEPT0007" se number nikal ke +1
    last_number = int(last_dept["department_id"].replace("DEPT", ""))
    new_number = last_number + 1

    # 4 digit padding ke saath return
    return f"DEPT{new_number:04d}"


# ==========================================================
# ROUTE 1 : DEPARTMENT LIST (Search + Filter + Trash)
# URL : GET /admin/departments/
# ==========================================================

@department_bp.route("/")
@role_required("admin")
def list_departments():

    # Query parameters nikalna
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    show_deleted = request.args.get("trash", "0") == "1"

    # Base query - trash dekhna hai ya normal list
    query = {"is_deleted": True} if show_deleted else {"is_deleted": {"$ne": True}}

    # Search by name ya department_id
    if search_query:
        query["$or"] = [
            {"name": {"$regex": search_query, "$options": "i"}},
            {"department_id": {"$regex": search_query, "$options": "i"}},
            {"description": {"$regex": search_query, "$options": "i"}},
        ]

    # Status filter (sirf jab trash nahi dekh rahe)
    if status_filter and not show_deleted:
        query["status"] = status_filter

    # Final query chalana - naye departments upar
    dept_list = list(departments.find(query).sort("created_at", -1))

    # Har department ke saath kitne active employees hain (extra info)
    for dept in dept_list:
        emp_count = employees.count_documents({
            "department": dept["name"],
            "is_deleted": {"$ne": True}
        })
        dept["employee_count"] = emp_count

    return render_template(
        "admin/departments/list.html",
        departments=dept_list,
        search_query=search_query,
        status_filter=status_filter,
        show_deleted=show_deleted,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : ADD DEPARTMENT
# URL : GET + POST /admin/departments/add
# ==========================================================

@department_bp.route("/add", methods=["GET", "POST"])
@role_required("admin")
def add_department():

    if request.method == "POST":

        # Form se data nikalna
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        head = request.form.get("head", "").strip()
        location = request.form.get("location", "").strip()
        budget = request.form.get("budget", "0")

        # Required fields check
        if not name:
            flash("Department name is required.", "danger")
            return redirect(url_for("departments.add_department"))

        # Same name se active department already exist to hai kya?
        if departments.find_one({"name": name, "is_deleted": {"$ne": True}}):
            flash("A department with this name already exists.", "danger")
            return redirect(url_for("departments.add_department"))

        # Naya document insert
        departments.insert_one({
            "department_id": generate_department_id(),
            "name": name,
            "description": description,
            "head": head,
            "location": location,
            "budget": float(budget) if budget else 0,
            "status": "Active",
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        flash(f"Department '{name}' added successfully.", "success")
        return redirect(url_for("departments.list_departments"))

    # GET request -> sirf form dikhana
    return render_template(
        "admin/departments/add.html",
        username=session["username"],
        role=session["role"],
    )

# ==========================================================
# ROUTE 3 : EDIT DEPARTMENT
# URL : /admin/departments/edit/<department_id>
# ==========================================================

@department_bp.route("/edit/<department_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_department(department_id):

    # Pehle department dhundo
    department = departments.find_one({"department_id": department_id})

    if not department:
        flash("Department not found.", "danger")
        return redirect(url_for("departments.list_departments"))

    if request.method == "POST":

        update_data = {
            "name": request.form.get("name", "").strip(),
            "description": request.form.get("description", "").strip(),
            "head": request.form.get("head", "").strip(),
            "location": request.form.get("location", "").strip(),
            "budget": float(request.form.get("budget") or 0),
            "status": request.form.get("status", "Active"),
            "updated_at": datetime.utcnow(),
        }

        # Name empty nahi hona chahiye
        if not update_data["name"]:
            flash("Department name is required.", "danger")
            return redirect(url_for("departments.edit_department", department_id=department_id))

        # Duplicate name check (khud ke alawa)
        existing = departments.find_one({
            "name": update_data["name"],
            "department_id": {"$ne": department_id},
            "is_deleted": {"$ne": True}
        })
        if existing:
            flash("Another department with this name already exists.", "danger")
            return redirect(url_for("departments.edit_department", department_id=department_id))

        # Update kar do
        departments.update_one(
            {"department_id": department_id},
            {"$set": update_data}
        )

        flash("Department updated successfully.", "success")
        return redirect(url_for("departments.view_department", department_id=department_id))

    # GET -> edit form with existing data
    return render_template(
        "admin/departments/edit.html",
        department=department,
        username=session["username"],
        role=session["role"],
    )
# ==========================================================
# ROUTE 4 : VIEW DEPARTMENT (Profile)
# URL : /admin/departments/view/<department_id>
# ==========================================================

@department_bp.route("/view/<department_id>")
@role_required("admin")
def view_department(department_id):

    department = departments.find_one({"department_id": department_id})

    if not department:
        flash("Department not found.", "danger")
        return redirect(url_for("departments.list_departments"))

    # Is department ke active employees bhi dikha denge
    dept_employees = list(employees.find({
        "department": department["name"],
        "is_deleted": {"$ne": True}
    }).sort("full_name", 1))

    return render_template(
        "admin/departments/profile.html",
        department=department,
        dept_employees=dept_employees,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 5 : SOFT DELETE
# ==========================================================

@department_bp.route("/delete/<department_id>", methods=["POST"])
@role_required("admin")
def soft_delete_department(department_id):

    departments.update_one(
        {"department_id": department_id},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )

    flash("Department moved to Trash.", "success")
    return redirect(url_for("departments.list_departments"))


# ==========================================================
# ROUTE 6 : RESTORE
# ==========================================================

@department_bp.route("/restore/<department_id>", methods=["POST"])
@role_required("admin")
def restore_department(department_id):

    departments.update_one(
        {"department_id": department_id},
        {"$set": {"is_deleted": False, "updated_at": datetime.utcnow()}}
    )

    flash("Department restored successfully.", "success")
    return redirect(url_for("departments.list_departments", trash=1))


# ==========================================================
# ROUTE 7 : PERMANENT DELETE
# ==========================================================

@department_bp.route("/delete-permanent/<department_id>", methods=["POST"])
@role_required("admin")
def permanent_delete_department(department_id):

    departments.delete_one({"department_id": department_id})

    flash("Department permanently deleted.", "success")
    return redirect(url_for("departments.list_departments", trash=1))