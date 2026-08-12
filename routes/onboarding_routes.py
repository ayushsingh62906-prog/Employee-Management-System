# ==========================================================
# FILE : routes/onboarding_routes.py
# PURPOSE : Onboarding Workflow
#           1. HR document upload link generate karta hai
#           2. Candidate documents upload karta hai (PUBLIC)
#           3. HR documents verify karta hai (checkboxes)
#           4. HR Admin ko notify karta hai
#           5. Admin final approval deta hai (onboarding_routes
#              mein nahi - job_routes.py ke onboard_candidate()
#              mein hi hai, sirf uska access admin-only kar
#              denge - alag step mein)
# ==========================================================

import os
import uuid
from datetime import datetime
from bson import ObjectId

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from werkzeug.utils import secure_filename

from db import recruitment
from utils.decorators import role_required


onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

UPLOAD_FOLDER = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "static", "uploads", "onboarding_docs"
)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ==========================================================
# ROUTE 1 : DOCUMENT UPLOAD LINK GENERATE KARNA
# HR/Admin trigger karte hain, Selected candidate ke liye
# URL : POST /onboarding/generate-doc-link/<app_id>
# ==========================================================

@onboarding_bp.route("/generate-doc-link/<app_id>", methods=["POST"])
@role_required("hr", "admin")
def generate_doc_link(app_id):

    application = recruitment.find_one({"_id": ObjectId(app_id), "type": "application"})

    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for("jobs.list_jobs"))

    token = uuid.uuid4().hex

    recruitment.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {
            "doc_token": token,
            "doc_status": "Pending Upload",
            "id_proof_verified": False,
            "bank_details_verified": False,
            "doc_link_generated_at": datetime.utcnow(),
        }}
    )

    doc_link = url_for("onboarding.upload_documents", token=token, _external=True)

    flash(f"Document upload link generated: {doc_link}", "success")
    return redirect(url_for("jobs.view_applications", job_id=application["job_id"]))


# ==========================================================
# ROUTE 2 : CANDIDATE DOCUMENTS UPLOAD KARE
# PUBLIC route - login nahi chahiye
# URL : GET/POST /onboarding/upload/<token>
# ==========================================================

@onboarding_bp.route("/upload/<token>", methods=["GET", "POST"])
def upload_documents(token):

    application = recruitment.find_one({"doc_token": token, "type": "application"})

    if not application:
        return render_template("public/doc_invalid.html")

    # Agar already upload kar chuka hai, dobara form nahi dikhana
    if application.get("doc_status") == "Uploaded":
        return render_template("public/doc_already_uploaded.html")

    if request.method == "POST":

        bank_account_number = request.form.get("bank_account_number", "").strip()
        bank_ifsc = request.form.get("bank_ifsc", "").strip()

        id_proof_file = request.files.get("id_proof")
        bank_proof_file = request.files.get("bank_proof")

        if not id_proof_file or not id_proof_file.filename:
            flash("ID Proof file is required.", "danger")
            return redirect(url_for("onboarding.upload_documents", token=token))

        if not bank_proof_file or not bank_proof_file.filename:
            flash("Bank Proof file is required.", "danger")
            return redirect(url_for("onboarding.upload_documents", token=token))

        if not allowed_file(id_proof_file.filename) or not allowed_file(bank_proof_file.filename):
            flash("Only PDF, PNG, JPG files are allowed.", "danger")
            return redirect(url_for("onboarding.upload_documents", token=token))

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # -----------------------------
        # ID Proof save karna
        # -----------------------------
        id_ext = id_proof_file.filename.rsplit(".", 1)[1].lower()
        id_proof_filename = secure_filename(
            f"{token}_idproof_{int(datetime.utcnow().timestamp())}.{id_ext}"
        )
        id_proof_file.save(os.path.join(UPLOAD_FOLDER, id_proof_filename))

        # -----------------------------
        # Bank Proof save karna
        # -----------------------------
        bank_ext = bank_proof_file.filename.rsplit(".", 1)[1].lower()
        bank_proof_filename = secure_filename(
            f"{token}_bankproof_{int(datetime.utcnow().timestamp())}.{bank_ext}"
        )
        bank_proof_file.save(os.path.join(UPLOAD_FOLDER, bank_proof_filename))

        recruitment.update_one(
            {"doc_token": token},
            {"$set": {
                "doc_status": "Uploaded",
                "id_proof_file": id_proof_filename,
                "bank_proof_file": bank_proof_filename,
                "bank_account_number": bank_account_number,
                "bank_ifsc": bank_ifsc,
                "doc_uploaded_at": datetime.utcnow(),
            }}
        )

        return render_template("public/doc_upload_success.html")

    return render_template(
        "public/doc_upload_form.html",
        candidate_name=application.get("full_name"),
        job_title=application.get("job_title"),
        token=token,
    )
    
    # ==========================================================
# ROUTE 3 : ID Proof / Bank Details Verify Toggle (HR/Admin)
# Bilkul No-Due Clearance jaisa pattern - checkbox tick/untick
# URL : POST /onboarding/verify/<app_id>/<doc_type>
# ==========================================================

@onboarding_bp.route("/verify/<app_id>/<doc_type>", methods=["POST"])
@role_required("hr", "admin")
def toggle_doc_verification(app_id, doc_type):

    valid_types = {
        "id": "id_proof_verified",
        "bank": "bank_details_verified",
    }

    if doc_type not in valid_types:
        flash("Invalid verification type.", "danger")
        return redirect(url_for("jobs.list_jobs"))

    field_name = valid_types[doc_type]

    application = recruitment.find_one({"_id": ObjectId(app_id), "type": "application"})

    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for("jobs.list_jobs"))

    current_value = application.get(field_name, False)

    recruitment.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {field_name: not current_value}}
    )

    return redirect(url_for("jobs.view_applications", job_id=application["job_id"]))


# ==========================================================
# ROUTE 4 : ADMIN KO NOTIFY KARNA
# Sirf tab enable jab dono documents verify ho chuke hon
# URL : POST /onboarding/notify-admin/<app_id>
# ==========================================================

@onboarding_bp.route("/notify-admin/<app_id>", methods=["POST"])
@role_required("hr", "admin")
def notify_admin(app_id):

    application = recruitment.find_one({"_id": ObjectId(app_id), "type": "application"})

    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for("jobs.list_jobs"))

    # -----------------------------
    # SECURITY: Backend pe bhi check - dono verified
    # hone chahiye, frontend disable button bypass ho
    # sakta hai (Postman se), isliye yahan bhi check zaroori
    # -----------------------------
    if not (application.get("id_proof_verified") and application.get("bank_details_verified")):
        flash("Cannot notify Admin — both ID Proof and Bank Details must be verified first.", "warning")
        return redirect(url_for("jobs.view_applications", job_id=application["job_id"]))

    recruitment.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {
            "status": "Pending Onboarding",
            "notified_admin_at": datetime.utcnow(),
            "notified_by": session.get("username"),
        }}
    )

    flash("Admin notified successfully. Candidate is now pending Admin's approval.", "success")
    return redirect(url_for("jobs.view_applications", job_id=application["job_id"]))

# ==========================================================
# ROUTE 5 : ADMIN KA "PENDING ONBOARDING" QUEUE
# Sirf Admin dekh sakta hai - jo candidates HR ne notify
# kiye hain, unhi ki list yahan dikhegi
# URL : GET /onboarding/pending
# ==========================================================

@onboarding_bp.route("/pending")
@role_required("admin")
def list_pending_onboarding():

    pending_list = list(recruitment.find({
        "type": "application",
        "status": "Pending Onboarding"
    }).sort("notified_admin_at", -1))

    return render_template(
        "admin/onboarding/pending.html",
        pending_list=pending_list,
        username=session["username"],
        role=session["role"],
    )