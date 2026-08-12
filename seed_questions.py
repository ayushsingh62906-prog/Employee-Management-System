# ==========================================================
# FILE : seed_questions.py
# PURPOSE : Sample/dummy MCQ questions database mein daalna
#           (testing ke liye) - ye file SIRF EK BAAR run karni hai
#
# Run karne ka tarika:
#   cd backend
#   python ../seed_questions.py
#   (ya jaha bhi tera project root hai, wahan se)
# ==========================================================

import sys
import os

# Project root ko path mein daal rahe hain taaki db.py import ho sake
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from db import exam_questions


# ==========================================================
# 20 SAMPLE MCQ QUESTIONS (General + Basic Tech mix)
#
# Format: question, 4 options, correct_option (0-indexed)
# ==========================================================

sample_questions = [
    {
        "question": "What does 'HTML' stand for?",
        "options": ["Hyper Text Markup Language", "High Tech Modern Language", "Hyperlink Text Management Language", "Home Tool Markup Language"],
        "correct_option": 0,
    },
    {
        "question": "Which data structure uses FIFO (First In First Out)?",
        "options": ["Stack", "Queue", "Tree", "Graph"],
        "correct_option": 1,
    },
    {
        "question": "What is the time complexity of binary search?",
        "options": ["O(n)", "O(n^2)", "O(log n)", "O(1)"],
        "correct_option": 2,
    },
    {
        "question": "Which of these is NOT a programming language?",
        "options": ["Python", "Java", "HTML", "C++"],
        "correct_option": 2,
    },
    {
        "question": "In MongoDB, data is stored in the form of:",
        "options": ["Tables and Rows", "Documents (BSON)", "XML files", "Sheets"],
        "correct_option": 1,
    },
    {
        "question": "What does 'CSS' primarily control on a webpage?",
        "options": ["Server logic", "Database queries", "Visual styling and layout", "Network requests"],
        "correct_option": 2,
    },
    {
        "question": "Which HTTP method is typically used to submit form data?",
        "options": ["GET", "POST", "DELETE", "HEAD"],
        "correct_option": 1,
    },
    {
        "question": "What is the full form of 'API'?",
        "options": ["Application Programming Interface", "Advanced Program Instruction", "Applied Programming Interaction", "Application Process Integration"],
        "correct_option": 0,
    },
    {
        "question": "Which of these is a version control system?",
        "options": ["Git", "MongoDB", "Flask", "React"],
        "correct_option": 0,
    },
    {
        "question": "What does 'CRUD' stand for in software development?",
        "options": ["Create, Read, Update, Delete", "Copy, Run, Undo, Debug", "Create, Run, Upload, Download", "Compile, Read, Update, Deploy"],
        "correct_option": 0,
    },
    {
        "question": "Which of the following is used for client-side scripting?",
        "options": ["Python", "JavaScript", "SQL", "PHP"],
        "correct_option": 1,
    },
    {
        "question": "In Python, which keyword is used to define a function?",
        "options": ["func", "def", "function", "define"],
        "correct_option": 1,
    },
    {
        "question": "What is the primary purpose of a firewall?",
        "options": ["Speed up internet", "Store data", "Block unauthorized network access", "Compress files"],
        "correct_option": 2,
    },
    {
        "question": "Which of these is a NoSQL database?",
        "options": ["MySQL", "PostgreSQL", "MongoDB", "Oracle"],
        "correct_option": 2,
    },
    {
        "question": "What does 'SQL' stand for?",
        "options": ["Structured Query Language", "Simple Question Language", "Sequential Query Logic", "Server Query Language"],
        "correct_option": 0,
    },
    {
        "question": "Which of these best describes 'debugging'?",
        "options": ["Writing new code", "Finding and fixing errors in code", "Deleting old code", "Designing UI"],
        "correct_option": 1,
    },
    {
        "question": "What is the main advantage of using Git branches?",
        "options": ["Faster internet", "Working on features independently without affecting main code", "Smaller file sizes", "Automatic bug fixing"],
        "correct_option": 1,
    },
    {
        "question": "Which company developed the React library?",
        "options": ["Google", "Microsoft", "Meta (Facebook)", "Amazon"],
        "correct_option": 2,
    },
    {
        "question": "What does 'REST' stand for in RESTful APIs?",
        "options": ["Representational State Transfer", "Remote End State Transfer", "Reliable Server Transfer", "Random Execution State Transfer"],
        "correct_option": 0,
    },
    {
        "question": "Which of these is used to style a Flask web page?",
        "options": ["Jinja", "CSS", "SQL", "JSON"],
        "correct_option": 1,
    },
]


def run_seed():

    # Agar already questions hain, dobara insert mat karo
    existing_count = exam_questions.count_documents({})

    if existing_count > 0:
        print(f"Already {existing_count} questions maujood hain database mein. Seeding skip kar rahe hain.")
        return

    exam_questions.insert_many(sample_questions)
    print(f"{len(sample_questions)} sample questions successfully insert ho gaye!")


if __name__ == "__main__":
    run_seed()