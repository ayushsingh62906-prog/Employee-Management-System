# ==========================================================
# FILE : utils/decorators.py
# PURPOSE : Reusable decorators for Login Check aur
#           Role Based Access Control (RBAC)
# ==========================================================

# functools se "wraps" import kar rahe hain.
# Isse decorator lagane ke baad bhi original function ka
# naam/docstring preserve rehta hai (Flask ke url_for ke
# liye zaroori hai, warna "View function mapping is
# overwriting an existing endpoint" error aa sakta hai)
from functools import wraps

# session -> login ke time jo data store kiya tha (user_id, role)
#            usko yahan check karenge
# flash    -> user ko warning/error message dikhane ke liye
# redirect, url_for -> kisi page pe bhej dene ke liye
from flask import session, flash, redirect, url_for


# ==========================================================
# LOGIN REQUIRED DECORATOR
#
# Use kaise karna hai:
#
# @login_required
# def kisi_bhi_route():
#     ...
#
# Isse pehle ye check hoga ki user login hai ya nahi,
# tabhi asli route function chalega.
# ==========================================================

def login_required(view_func):
    # view_func = wo original function jispe hum
    # @login_required laga rahe hain (jaise admin_dashboard)

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # *args, **kwargs isliye taaki agar route ko koi
        # parameter mil raha ho (jaise employee_id) to wo
        # bhi wrapper se hote hue original function tak pahunche

        # -----------------------------
        # Step 1 : Session me user_id hai ya nahi check karo
        # -----------------------------
        if "user_id" not in session:

            # Agar login nahi hai to warning dikha ke
            # login page pe bhej do
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        # -----------------------------
        # Step 2 : Agar login hai to original function
        # ko normally chalne do
        # -----------------------------
        return view_func(*args, **kwargs)

    # decorator hamesha wrapper function return karta hai,
    # Flask isi wrapper ko route ke against register karta hai
    return wrapper


# ==========================================================
# ROLE REQUIRED DECORATOR
#
# Use kaise karna hai:
#
# @role_required("admin")             -> sirf admin allow
# @role_required("admin", "hr")       -> admin ya hr dono allow
#
# Ye login_required se ek level upar hai kyunki isme
# "allowed_roles" bhi pass karne hain, isliye ek extra
# function layer (decorator) lagta hai.
# ==========================================================

def role_required(*allowed_roles):
    # allowed_roles ek tuple hoga, jaise ("admin",) ya ("admin","hr")
    # kyunki humne *allowed_roles likha hai (variable arguments)

    # Ye outer function hai jo asli decorator return karega
    def decorator(view_func):

        @wraps(view_func)
        def wrapper(*args, **kwargs):

            # -----------------------------
            # Step 1 : Pehle login check
            # (agar login hi nahi hai to role check
            # karne ka koi matlab nahi)
            # -----------------------------
            if "user_id" not in session:
                flash("Please login first.", "warning")
                return redirect(url_for("login"))

            # -----------------------------
            # Step 2 : Ab role check
            # -----------------------------

            # session me jo role save hai usko lowercase kar rahe
            # hain taaki "Admin" aur "admin" dono match ho jayein
            user_role = session.get("role", "").lower()

            # allowed_roles list ("admin","hr") ko bhi lowercase
            # me convert kar rahe hain, same reason se
            allowed = [r.lower() for r in allowed_roles]

            # agar current user ka role allowed list me nahi hai
            if user_role not in allowed:
                flash("Access Denied!", "danger")
                return redirect(url_for("login"))

            # -----------------------------
            # Step 3 : Sab check pass ho gaya,
            # ab asli route function chalao
            # -----------------------------
            return view_func(*args, **kwargs)

        return wrapper

    # decorator() function return ho raha hai, jo aage
    # jaake @role_required("admin") likhne pe use hoga
    return decorator