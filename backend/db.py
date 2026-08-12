# MongoDB se connect karne ke liye MongoClient import kar rahe hain
from pymongo import MongoClient

# .env file ko load karne ke liye
from dotenv import load_dotenv

# Environment variables (jaise MONGO_URI) ko access karne ke liye
import os

# SSL certificate verify karne ke liye
# Ye MongoDB Atlas ke secure connection me use hota hai
import certifi


# ============================================================
# .env file load karna
# Iske baad .env me likhe saare variables Python use kar sakta hai
# ============================================================
load_dotenv()


# ============================================================
# .env file se MongoDB Connection String lena
# Example:
# MONGO_URI = mongodb+srv://username:password@cluster.....
# ============================================================
MONGO_URI = os.getenv("MONGO_URI")


# ============================================================
# MongoDB Atlas se connection banana
#
# MongoClient() database server se connect karta hai
#
# tlsCAFile = SSL Certificate verify karta hai
# Taaki connection secure rahe
# ============================================================
client = MongoClient(
    MONGO_URI,
    tlsCAFile=certifi.where()
)


# ============================================================
# Database Select karna
#
# Agar employee_management_system database
# pehle se nahi bana hai
# to MongoDB first insert ke time automatically create kar dega.
# ============================================================
db = client["employee_management_system"]


# ============================================================
# users Collection Select karna
#
# SQL me Table hoti hai
# MongoDB me Collection hoti hai
#
# Is collection me Register/Login ka sara data store hoga.
# ============================================================
users = db["users"]




# ==========================================================
# Collections
# ==========================================================

users = db["users"]

employees = db["employees"]

departments = db["departments"]

attendance = db["attendance"]

leave_requests = db["leave_requests"]

salary = db["salary"]

performance = db["performance"]

recruitment = db["recruitment"]

exam_questions = db["exam_questions"]

notifications = db["notifications"]

documents = db["documents"]

reports = db["reports"]

# ============================================================
# Testing Purpose
#
# Agar ye message terminal me print ho gaya
# to iska matlab MongoDB Atlas se
# successful connection establish ho gaya.
# ============================================================
print("✅ MongoDB Connected Successfully")