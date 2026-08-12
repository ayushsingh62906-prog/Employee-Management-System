# ==========================================================
# FILE : routes/exam_routes.py
# PURPOSE : AI Interview / Online MCQ Exam Feature
#           - HR shortlisted candidate ke liye exam link generate karta hai
#           - Candidate (bina login) exam deta hai
#           - System auto-evaluate karke Selected/Rejected decide karta hai
# ==========================================================

import uuid
from datetime import datetime

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from bson import ObjectId

from db import recruitment, exam_questions
from utils.decorators import role_required


exam_bp = Blueprint(
    "exam",
    __name__,
    url_prefix="/exam"
)


# ==========================================================
# CONFIG
# Pass threshold ek hi jagah define hai, badalna ho to
# bas ye number change karna
# ==========================================================
PASS_THRESHOLD_PERCENT = 50

# Max kitne questions exam mein dikhane hain (dummy bank mein
# abhi sirf 20 hain, isliye jitne available hain utne hi milenge)
MAX_QUESTIONS = 60


# ==========================================================
# ROUTE 1 : GENERATE EXAM LINK
# HR/Admin ek Shortlisted candidate ke liye unique link banata hai
# ==========================================================

@exam_bp.route("/generate/<app_id>", methods=["POST"])
@role_required("hr", "admin")
def generate_exam_link(app_id):

    try:
        app_doc = recruitment.find_one({"_id": ObjectId(app_id), "type": "application"})
    except Exception:
        flash("Invalid application.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    if not app_doc:
        flash("Application not found.", "danger")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    # Sirf Shortlisted candidates ke liye hi exam link ban sakta hai
    if app_doc.get("status") != "Shortlisted":
        flash("Only Shortlisted candidates can be given an exam.", "warning")
        return redirect(request.referrer or url_for("jobs.list_jobs"))

    # Unique token generate karna (URL mein use hoga)
    exam_token = uuid.uuid4().hex

    recruitment.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {
            "exam_token": exam_token,
            "exam_status": "Not Started",   # Not Started -> In Progress -> Completed
            "exam_score": None,
            "exam_question_ids": [],        # exam start hote hi fill hoga
            "exam_link_generated_by": session.get("username"),
            "exam_link_generated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }}
    )

    # Poora shareable link banana (candidate ko HR manually bhejega)
    exam_link = request.host_url.rstrip("/") + url_for("exam.take_exam", token=exam_token)

    flash("Exam link generated successfully. Copy and share it with the candidate.", "success")

    # Link ko query param mein bhej rahe hain taaki applications.html
    # ek copy-box mein dikha sake (Step 5 mein wiring karenge)
    redirect_url = request.referrer or url_for("jobs.list_jobs")
    separator = "&" if "?" in redirect_url else "?"
    return redirect(f"{redirect_url}{separator}exam_link={exam_link}")


# ==========================================================
# ROUTE 2 : TAKE EXAM (Candidate ka exam page)
# PUBLIC - koi login/role_required nahi (candidate ke paas account nahi hota)
# ==========================================================

@exam_bp.route("/take/<token>", methods=["GET"])
def take_exam(token):

    app_doc = recruitment.find_one({"exam_token": token, "type": "application"})

    if not app_doc:
        flash("Invalid or expired exam link.", "danger")
        return redirect(url_for("home"))

    # Agar candidate pehle hi submit kar chuka hai
    if app_doc.get("exam_status") == "Completed":
        return render_template("public/exam_already_submitted.html")

    # -----------------------------------------------------
    # Questions decide karna:
    # Agar pehli baar page khul raha hai (exam_question_ids khali hai)
    # to naye random questions sample karke DB mein save kar do.
    #
    # Agar candidate ne page REFRESH kiya hai (exam already
    # "In Progress" hai aur ids pehle se saved hain), to wahi
    # SAME questions dobara dikhao - naye random nahi lena,
    # warna submit ke waqt scoring galat ho jayegi.
    # -----------------------------------------------------
    saved_question_ids = app_doc.get("exam_question_ids") or []

    if not saved_question_ids:
        # Available questions ka count check karo (dummy bank mein 20 hain)
        available_count = exam_questions.count_documents({})
        sample_size = min(MAX_QUESTIONS, available_count)

        sampled = list(exam_questions.aggregate([
            {"$sample": {"size": sample_size}}
        ]))

        saved_question_ids = [str(q["_id"]) for q in sampled]

        recruitment.update_one(
            {"_id": app_doc["_id"]},
            {"$set": {
                "exam_question_ids": saved_question_ids,
                "exam_status": "In Progress",
                "exam_started_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }}
        )

        questions = sampled
    else:
        # Refresh case - wahi saved questions dobara fetch karo
        object_ids = [ObjectId(qid) for qid in saved_question_ids]
        questions = list(exam_questions.find({"_id": {"$in": object_ids}}))

    if not questions:
        flash("No exam questions available right now.", "danger")
        return redirect(url_for("home"))

    return render_template(
        "public/exam_take.html",
        token=token,
        candidate_name=app_doc.get("full_name", "Candidate"),
        questions=questions,
    )


# ==========================================================
# ROUTE 3 : SUBMIT EXAM
# PUBLIC - candidate answers submit karta hai, auto-evaluate hota hai
# ==========================================================

@exam_bp.route("/submit/<token>", methods=["POST"])
def submit_exam(token):

    app_doc = recruitment.find_one({"exam_token": token, "type": "application"})

    if not app_doc:
        flash("Invalid or expired exam link.", "danger")
        return redirect(url_for("home"))

    # Agar already submit ho chuka hai (double-submit / back button se)
    if app_doc.get("exam_status") == "Completed":
        return render_template("public/exam_already_submitted.html")

    # Wahi question ids use karo jo candidate ko GET pe dikhaye gaye the
    # (form se aaye kisi bhi extra/tampered id ko IGNORE kar rahe hain)
    saved_question_ids = app_doc.get("exam_question_ids") or []

    if not saved_question_ids:
        flash("Something went wrong. Please contact HR.", "danger")
        return redirect(url_for("home"))

    object_ids = [ObjectId(qid) for qid in saved_question_ids]
    questions = list(exam_questions.find({"_id": {"$in": object_ids}}))

    total_questions = len(questions)
    correct_count = 0

    for q in questions:
        qid_str = str(q["_id"])

        # Form field naming convention: q_<question_id>
        selected_option = request.form.get(f"q_{qid_str}")

        if selected_option is not None:
            try:
                if int(selected_option) == q.get("correct_option"):
                    correct_count += 1
            except (ValueError, TypeError):
                pass  # invalid/missing answer = wrong, kuch nahi karna

    # Score percentage nikalna
    if total_questions > 0:
        score_percent = round((correct_count / total_questions) * 100, 2)
    else:
        score_percent = 0

    # Threshold ke hisaab se Selected/Rejected decide karna
    final_status = "Selected" if score_percent >= PASS_THRESHOLD_PERCENT else "Rejected"

    recruitment.update_one(
        {"_id": app_doc["_id"]},
        {"$set": {
            "exam_status": "Completed",
            "exam_score": score_percent,
            "exam_correct_count": correct_count,
            "exam_total_questions": total_questions,
            "exam_submitted_at": datetime.utcnow(),
            "status": final_status,
            "updated_at": datetime.utcnow(),
        }}
    )

    # Candidate ko score NAHI dikha rahe - sirf submission confirm
    return render_template("public/exam_result.html", candidate_name=app_doc.get("full_name", "Candidate"))