# ==========================================================
# FILE : routes/job_routes.py
# PURPOSE : HR - Job Openings Management
#           Add / List / Edit / Delete Job Posts
# ==========================================================
from utils.resume_screening import screen_resume



from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import recruitment   # jobs is collection me save karenge
from utils.decorators import role_required


job_bp = Blueprint(
    "jobs",
    __name__,
    url_prefix="/hr/jobs"
)


# ==========================================================
# ROUTE 1 : JOB LIST
# ==========================================================

@job_bp.route("/")
@role_required("hr", "admin")
def list_jobs():

    jobs = list(recruitment.find({"type": "job"}).sort("created_at", -1))

    return render_template(
        "hr/jobs/list.html",
        jobs=jobs,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : ADD JOB
# ==========================================================

@job_bp.route("/add", methods=["GET", "POST"])
@role_required("hr", "admin")
def add_job():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        department = request.form.get("department", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "Full-time")
        experience = request.form.get("experience", "").strip()
        description = request.form.get("description", "").strip()
        requirements = request.form.get("requirements", "").strip()

        if not title or not description:
            flash("Title and description are required.", "danger")
            return redirect(url_for("jobs.add_job"))

        recruitment.insert_one({
            "type": "job",
            "title": title,
            "department": department,
            "location": location,
            "job_type": job_type,
            "experience": experience,
            "description": description,
            "requirements": requirements,
            "status": "Open",
            "posted_by": session.get("username"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        flash("Job opening posted successfully.", "success")
        return redirect(url_for("jobs.list_jobs"))

    return render_template(
        "hr/jobs/add.html",
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 3 : DELETE JOB
# ==========================================================

@job_bp.route("/delete/<job_id>", methods=["POST"])
@role_required("hr", "admin")
def delete_job(job_id):

    from bson import ObjectId

    try:
        recruitment.delete_one({"_id": ObjectId(job_id)})
        flash("Job deleted successfully.", "success")
    except:
        flash("Invalid job.", "danger")

    return redirect(url_for("jobs.list_jobs"))

# ==========================================================
# ROUTE 4 : PUBLIC APPLY PAGE (kisi bhi job ke liye)
# URL : /apply/<job_id>
# ==========================================================

@job_bp.route("/apply/<job_id>", methods=["GET", "POST"])
def apply_job(job_id):

    from bson import ObjectId
    import os
    from werkzeug.utils import secure_filename

    try:
        job = recruitment.find_one({"_id": ObjectId(job_id), "type": "job"})
    except:
        flash("Invalid job.", "danger")
        return redirect(url_for("home"))

    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        experience = request.form.get("experience", "").strip()
        cover_letter = request.form.get("cover_letter", "").strip()

        if not full_name or not email:
            flash("Name and email are required.", "danger")
            return redirect(url_for("jobs.apply_job", job_id=job_id))

        # Resume upload
        resume_file = request.files.get("resume")
        resume_filename = None
        match_score = 0.0 
        
        if resume_file and resume_file.filename:
            allowed = {"pdf", "doc", "docx"}
            ext = resume_file.filename.rsplit(".", 1)[-1].lower()
            if ext in allowed:
                upload_folder = os.path.join(
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
                    "static", "uploads", "resumes"
                )
                os.makedirs(upload_folder, exist_ok=True)
                resume_filename = secure_filename(
                    f"{email.split('@')[0]}_{int(datetime.utcnow().timestamp())}.{ext}"
                )
                resume_path = os.path.join(upload_folder, resume_filename)
                resume_file.save(resume_path)
                
                
                match_score = screen_resume(
                  resume_path,
                  job.get("description", ""),
                  job.get("requirements", "")
                )


        # Candidate save
        recruitment.insert_one({
            "type": "application",
            "job_id": str(job["_id"]),
            "job_title": job.get("title"),
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "experience": experience,
            "cover_letter": cover_letter,
            "resume": resume_filename,
            "match_score": match_score,
            "status": "Applied",          # Applied → Screening → Shortlisted → Rejected
            "created_at": datetime.utcnow(),
        })

        flash("Application submitted successfully! We will contact you soon.", "success")
        return redirect(url_for("home"))

    return render_template(
        "public/apply.html",
        job=job
    )


# ==========================================================
# ROUTE 5 : HR - View Applications for a Job
# ==========================================================

@job_bp.route("/applications/<job_id>")
@role_required("hr", "admin")
def view_applications(job_id):

    from bson import ObjectId

    try:
        job = recruitment.find_one({"_id": ObjectId(job_id)})
    except:
        flash("Invalid job.", "danger")
        return redirect(url_for("jobs.list_jobs"))

    # Status filter
    status_filter = request.args.get("status", "")

    query = {
        "type": "application",
        "job_id": str(job_id)
    }

    if status_filter:
        query["status"] = status_filter

    applications = list(recruitment.find(query).sort("match_score", -1))

    return render_template(
        "hr/jobs/applications.html",
        job=job,
        applications=applications,
        username=session["username"],
        role=session["role"],
    )
    # ==========================================================
# ROUTE 6 : UPDATE APPLICATION STATUS (Screening)
# Shortlist / Reject / Move to Screening
# ==========================================================

@job_bp.route("/application/<app_id>/status", methods=["POST"])
@role_required("hr", "admin")
def update_application_status(app_id):

    from bson import ObjectId

    new_status = request.form.get("status", "").strip()
    notes = request.form.get("notes", "").strip()

    allowed_status = ["Applied", "Screening", "Shortlisted", "Rejected"]

    if new_status not in allowed_status:
        flash("Invalid status.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    try:
        update_data = {
            "status": new_status,
            "reviewed_by": session.get("username"),
            "reviewed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Agar notes diye hain to save karo
        if notes:
            update_data["screening_notes"] = notes

        recruitment.update_one(
            {"_id": ObjectId(app_id), "type": "application"},
            {"$set": update_data}
        )

        flash(f"Application marked as {new_status}.", "success")
    except Exception:
        flash("Invalid application.", "danger")

    return redirect(request.referrer or url_for("jobs.list_jobs"))

# ==========================================================
# ROUTE 7 : GENERATE / SAVE INTERVIEW LINK
# Sirf Shortlisted candidates ke liye
# ==========================================================

@job_bp.route("/application/<app_id>/interview", methods=["POST"])
@role_required("hr", "admin")
def set_interview(app_id):

    from bson import ObjectId

    interview_link = request.form.get("interview_link", "").strip()
    interview_date = request.form.get("interview_date", "").strip()
    interview_time = request.form.get("interview_time", "").strip()
    interview_mode = request.form.get("interview_mode", "Online")  # Online / Offline
    notes = request.form.get("notes", "").strip()

    if not interview_link and not interview_date:
        flash("Please provide at least Interview Link or Date.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    try:
        app = recruitment.find_one({"_id": ObjectId(app_id), "type": "application"})

        if not app:
            flash("Application not found.", "danger")
            return redirect(request.referrer or url_for("jobs.list_jobs"))

        if app.get("status") != "Shortlisted":
            flash("Only Shortlisted candidates can be scheduled for interview.", "warning")
            return redirect(request.referrer or url_for("jobs.list_jobs"))

        recruitment.update_one(
            {"_id": ObjectId(app_id)},
            {"$set": {
                "interview_link": interview_link,
                "interview_date": interview_date,
                "interview_time": interview_time,
                "interview_mode": interview_mode,
                "interview_notes": notes,
                "interview_scheduled_by": session.get("username"),
                "interview_scheduled_at": datetime.utcnow(),
                "status": "Interview Scheduled",   # naya status
                "updated_at": datetime.utcnow(),
            }}
        )

        flash("Interview scheduled successfully.", "success")
    except Exception:
        flash("Something went wrong.", "danger")

    return redirect(request.referrer or url_for("jobs.list_jobs"))

# ==========================================================
# ROUTE 8 : ONBOARDING - Convert Candidate to Employee
# Shortlisted / Interview Scheduled se Employee banata hai
# ==========================================================

@job_bp.route("/application/<app_id>/onboard", methods=["POST"])
@role_required("admin")
def onboard_candidate(app_id):

    from bson import ObjectId
    from db import employees, users

    try:
        app = recruitment.find_one({"_id": ObjectId(app_id), "type": "application"})
    except:
        flash("Invalid application.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    if not app:
        flash("Application not found.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    # Sirf Shortlisted / Interview Scheduled se onboard allow
    if app.get("status") not in ["Shortlisted", "Interview Scheduled", "Selected"]:
        flash("Only Shortlisted / Interview Scheduled candidates can be onboarded.", "warning")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    email = app.get("email", "").strip().lower()
    full_name = app.get("full_name", "").strip()

    if not email or not full_name:
        flash("Candidate name/email missing.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    # Pehle se employee to nahi hai same email se?
    if employees.find_one({"email": email, "is_deleted": {"$ne": True}}):
        flash("An employee with this email already exists.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    # ---------- Emp ID generate (employee_routes jaisa logic) ----------
    last_employee = employees.find_one(sort=[("_id", -1)])
    if not last_employee or "employee_id" not in last_employee:
        new_emp_id = "EMP0001"
    else:
        last_number = int(last_employee["employee_id"].replace("EMP", ""))
        new_emp_id = f"EMP{last_number + 1:04d}"

    # Job se department lena (agar available ho)
    job = None
    if app.get("job_id"):
        try:
            job = recruitment.find_one({"_id": ObjectId(app["job_id"])})
        except:
            pass

    department = (job.get("department") if job else "") or "General"
    designation = (job.get("title") if job else "") or "Employee"

    # ---------- 1. Employees collection me insert ----------
    employees.insert_one({
        "employee_id": new_emp_id,
        "full_name": full_name,
        "email": email,
        "phone": app.get("phone", ""),
        "department": department,
        "designation": designation,
        "employee_type": "Full-time",
        "date_of_joining": datetime.utcnow().strftime("%Y-%m-%d"),
        "salary": 0,
        "status": "Active",
        "is_deleted": False,
        "onboarded_from": "recruitment",
        "application_id": str(app["_id"]),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    # ---------- 2. Users collection me entry (password baad me set) ----------
    if not users.find_one({"email": email}):
        users.insert_one({
            "username": full_name,
            "email": email,
            "employee_id": new_emp_id,
            "password": None,
            "role": "employee",
            "password_set": False,
            "created_at": datetime.utcnow(),
        })

    # ---------- 3. Application status update ----------
    recruitment.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {
            "status": "Onboarded",
            "employee_id": new_emp_id,
            "onboarded_by": session.get("username"),
            "onboarded_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }}
    )

    flash(f"Candidate onboarded successfully! Emp ID: {new_emp_id}. Ask them to set password.", "success")
    return redirect(request.referrer or url_for("jobs.list_jobs"))