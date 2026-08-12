# ==========================================================
# FILE : routes/settings_routes.py
# PURPOSE : Common Settings - Change Password + Update Profile
# ==========================================================
 
import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
 
from db import users
from utils.decorators import login_required
 
 
settings_bp = Blueprint(
    "settings",
    __name__,
    url_prefix="/settings"
)
 
 
# Profile photo upload ke liye allowed extensions (Employee module jaisa hi)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
 
UPLOAD_FOLDER = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "static", "uploads", "profile_photos"
)
 
 
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )
 
 
# ==========================================================
# CHANGE PASSWORD (existing hai, isse touch nahi karna)
# ==========================================================
 
@settings_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
 
    if request.method == "POST":
 
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
 
        if not current_password or not new_password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect(url_for("settings.change_password"))
 
        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("settings.change_password"))
 
        if len(new_password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("settings.change_password"))
 
        # Current user
        user = users.find_one({"email": session.get("email")})
 
        if not user or not check_password_hash(user.get("password", ""), current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("settings.change_password"))
 
        # Update password
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "password": generate_password_hash(new_password),
                "updated_at": datetime.utcnow()
            }}
        )
 
        flash("Password changed successfully.", "success")
        return redirect(url_for("settings.change_password"))
 
    return render_template(
        "settings/change_password.html",
        username=session["username"],
        role=session["role"],
    )
 
 
# ==========================================================
# UPDATE PROFILE (NAYA) - Name, Phone, Photo
# ==========================================================
 
@settings_bp.route("/profile", methods=["GET", "POST"])
@login_required
def update_profile():
 
    # Current logged-in user ko session ke email se dhoondh rahe hain
    user = users.find_one({"email": session.get("email")})
 
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("login"))
 
    if request.method == "POST":
 
        # -----------------------------
        # Form se naam aur phone lena
        # -----------------------------
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
 
        if not full_name:
            flash("Name cannot be empty.", "danger")
            return redirect(url_for("settings.update_profile"))
 
        # Update karne wala data - shuru mein sirf naam/phone
        update_data = {
            "username": full_name,
            "phone": phone,
            "updated_at": datetime.utcnow(),
        }
 
        # -----------------------------
        # Agar nayi photo upload hui hai
        # (Employee module jaisa hi pattern)
        # -----------------------------
        photo = request.files.get("photo")
 
        if photo and photo.filename and allowed_file(photo.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = photo.filename.rsplit(".", 1)[1].lower()
            photo_filename = secure_filename(
                f"{user['_id']}_{int(datetime.utcnow().timestamp())}.{ext}"
            )
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))
            update_data["photo"] = photo_filename
 
        # -----------------------------
        # Database update karna
        # -----------------------------
        users.update_one(
            {"_id": user["_id"]},
            {"$set": update_data}
        )
 
        # -----------------------------
        # IMPORTANT: session bhi turant update karo,
        # taaki bina re-login kiye navbar/sidebar mein
        # naya naam/photo turant dikhe
        # -----------------------------
        session["username"] = full_name
 
        if "photo" in update_data:
            session["photo"] = update_data["photo"]
 
        flash("Profile updated successfully.", "success")
        return redirect(url_for("settings.update_profile"))
 
    # GET request -> form dikhana, existing data ke saath pre-filled
    return render_template(
        "settings/profile.html",
        user=user,
        username=session["username"],
        role=session["role"],
    )
 