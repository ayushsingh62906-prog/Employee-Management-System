# ==========================================================
# FILE : utils/resume_screening.py
# PURPOSE : Resume Screening (ML Feature)
#
# Technique: TF-IDF (Term Frequency-Inverse Document Frequency)
#            + Cosine Similarity
#
# Ye ek classical NLP/ML technique hai jo do texts (resume aur
# job requirements) ko numeric vectors mein convert karke unka
# "similarity score" nikalti hai. Koi training data ya model
# training ki zarurat nahi - ye "unsupervised" technique hai,
# turant kaam karti hai.
# ==========================================================

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ==========================================================
# STEP 1 : Resume file (PDF/DOCX) se plain text nikalna
# ==========================================================

def extract_text_from_resume(filepath):

    ext = filepath.rsplit(".", 1)[-1].lower()
    text = ""

    try:
        if ext == "pdf":
            import pdfplumber

            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        elif ext == "docx":
            import docx

            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"

        # Note: purana .doc format (binary, Word 97-2003) yahan
        # support nahi hai - iske liye extra heavy libraries
        # (textract, antiword) chahiye hoti hain. Agar .doc file
        # aayi, to text khali rahega aur score 0 ban jaayega.

    except Exception:
        text = ""

    return text.strip()


# ==========================================================
# STEP 2 : TF-IDF + Cosine Similarity se match score nikalna
# ==========================================================

def calculate_match_score(resume_text, job_text):

    # Agar dono mein se ek bhi khali hai, score 0 de do
    if not resume_text or not job_text:
        return 0.0

    # Dono texts ko ek list mein daal rahe hain, kyunki
    # TfidfVectorizer ek "corpus" (documents ki list) expect karta hai
    documents = [resume_text, job_text]

    # stop_words="english" -> common words (the, is, and, a...)
    # ko ignore kar dega, kyunki unse koi meaningful match nahi milta
    vectorizer = TfidfVectorizer(stop_words="english")

    # Har document ko numeric vector mein convert kar rahe hain
    tfidf_matrix = vectorizer.fit_transform(documents)

    # Dono vectors ke beech cosine similarity (0 se 1 ke beech)
    similarity = cosine_similarity(
        tfidf_matrix[0:1],   # resume ka vector
        tfidf_matrix[1:2]    # job requirements ka vector
    )[0][0]

    # 0-1 ko 0-100 percentage mein convert kar rahe hain
    score = round(float(similarity) * 100, 1)

    return score


# ==========================================================
# STEP 3 : Combined helper - dono steps ek saath
# ==========================================================

def screen_resume(resume_filepath, job_description, job_requirements):

    resume_text = extract_text_from_resume(resume_filepath)

    # Job ka description + requirements dono milake match karenge
    job_text = f"{job_description} {job_requirements}"

    score = calculate_match_score(resume_text, job_text)

    return score