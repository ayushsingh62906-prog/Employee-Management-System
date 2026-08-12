# ==========================================================
# FILE : routes/announcement_routes.py
# PURPOSE : Admin - Company Announcements
#           Post / View / Delete Announcements
# ==========================================================

from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import notifications   # hum notifications collection use kar rahe hain
from utils.decorators import role_required


announcement_bp = Blueprint(
    "announcements",
    __name__,
    url_prefix="/admin/announcements"
)

# ==========================================================
# ROUTE 1 : LIST ANNOUNCEMENTS
# ==========================================================

@announcement_bp.route("/")
@role_required("admin")
def list_announcements():

    # Latest pehle
    announcements = list(notifications.find(
        {"type": "announcement"}
    ).sort("created_at", -1))

    return render_template(
        "admin/announcements/list.html",
        announcements=announcements,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : ADD ANNOUNCEMENT
# ==========================================================

@announcement_bp.route("/add", methods=["GET", "POST"])
@role_required("admin")
def add_announcement():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()

        if not title or not message:
            flash("Title and message are required.", "danger")
            return redirect(url_for("announcements.add_announcement"))

        notifications.insert_one({
            "type": "announcement",
            "title": title,
            "message": message,
            "posted_by": session.get("username"),
            "created_at": datetime.utcnow(),
        })

        flash("Announcement posted successfully.", "success")
        return redirect(url_for("announcements.list_announcements"))

    return render_template(
        "admin/announcements/add.html",
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 3 : DELETE ANNOUNCEMENT
# ==========================================================

@announcement_bp.route("/delete/<ann_id>", methods=["POST"])
@role_required("admin")
def delete_announcement(ann_id):

    from bson import ObjectId

    try:
        notifications.delete_one({"_id": ObjectId(ann_id)})
        flash("Announcement deleted.", "success")
    except:
        flash("Invalid announcement.", "danger")

    return redirect(url_for("announcements.list_announcements"))