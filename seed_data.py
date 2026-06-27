"""
seed_data.py - Seeds the database with test accounts and courses.

Accounts created:
  admin@elearn.com    / Admin@123     (admin)
  faculty@elearn.com  / Faculty@123   (faculty)
  teacher@elearn.com  / Teacher@123   (faculty)
  student@elearn.com  / Student@123   (student)

Courses created (5 sample courses):
  Python for Beginners         (free)
  Web Development with Flask   (paid Rs.499)
  Cybersecurity Fundamentals   (paid Rs.999)
  UI/UX Design Basics          (free)
  Business Analytics           (paid Rs.799)

Usage:
    cd backend
    .venv\\Scripts\\python.exe seed_data.py
"""

import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext
from dotenv import load_dotenv
import uuid

load_dotenv()

DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "elearndb")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine           = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
pwd_ctx          = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
ACCOUNTS = [
    {"name": "Admin User",     "email": "admin@elearn.com",   "password": "Admin@123",   "role": "admin"},
    {"name": "Dr. Sarah Khan", "email": "faculty@elearn.com", "password": "Faculty@123", "role": "faculty"},
    {"name": "Prof. Ali Raza", "email": "teacher@elearn.com", "password": "Teacher@123", "role": "faculty"},
    {"name": "Ahmed Student",  "email": "student@elearn.com", "password": "Student@123", "role": "student"},
]

COURSES = [
    {
        "title":       "Python for Beginners",
        "description": "Learn Python from scratch. Covers variables, loops, functions, OOP and file handling.",
        "price":       0.0,
        "is_free":     True,
    },
    {
        "title":       "Web Development with Flask",
        "description": "Build real-world web apps using Python and Flask. Includes REST APIs, SQLAlchemy and auth.",
        "price":       499.0,
        "is_free":     False,
    },
    {
        "title":       "Cybersecurity Fundamentals",
        "description": "Master network security, ethical hacking, penetration testing and vulnerability assessment.",
        "price":       999.0,
        "is_free":     False,
    },
    {
        "title":       "UI/UX Design Basics",
        "description": "Learn Figma, design principles, wireframing, prototyping and usability testing.",
        "price":       0.0,
        "is_free":     True,
    },
    {
        "title":       "Business Analytics with Python",
        "description": "Use Python, Pandas and Matplotlib to analyse data, build dashboards and drive decisions.",
        "price":       799.0,
        "is_free":     False,
    },
]

# ---------------------------------------------------------------------------
# EXAMS & QUESTIONS
# Each exam is attached to a course by its title.
# ---------------------------------------------------------------------------

EXAMS = [
    {
        "course_title": "Python for Beginners",
        "title": "Python Basics Quiz",
        "duration_minutes": 15,
        "questions": [
            {
                "question_text": "What is the correct way to create a variable in Python?",
                "options": {"A": "var x = 5", "B": "x = 5", "C": "int x = 5", "D": "let x = 5"},
                "correct_answer": "B",
            },
            {
                "question_text": "Which keyword is used to define a function in Python?",
                "options": {"A": "function", "B": "func", "C": "def", "D": "define"},
                "correct_answer": "C",
            },
            {
                "question_text": "What does the `len()` function return?",
                "options": {"A": "The type of an object", "B": "The number of items in an object", "C": "The memory size of an object", "D": "The last element of a list"},
                "correct_answer": "B",
            },
            {
                "question_text": "Which of the following is a valid Python comment?",
                "options": {"A": "// This is a comment", "B": "/* This is a comment */", "C": "# This is a comment", "D": "<!-- This is a comment -->"},
                "correct_answer": "C",
            },
            {
                "question_text": "What is the output of `print(2 ** 3)` in Python?",
                "options": {"A": "6", "B": "9", "C": "8", "D": "23"},
                "correct_answer": "C",
            },
        ],
    },
]

# ---------------------------------------------------------------------------

def hash_pw(plain: str) -> str:
    return pwd_ctx.hash(plain)


async def user_exists(session, email):
    r = await session.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email})
    return r.fetchone()


async def seed_accounts(session):
    id_map = {}
    print("\n-- Accounts --")
    for acc in ACCOUNTS:
        row = await user_exists(session, acc["email"])
        if row:
            id_map[acc["email"]] = str(row[0])
            print(f"  [skip] {acc['email']} already exists")
            continue
        uid = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO users (id, name, email, password_hash, role, is_active, is_deleted, created_at, updated_at)
                VALUES (:id, :name, :email, :hp, :role, true, false, NOW(), NOW())
            """),
            {"id": uid, "name": acc["name"], "email": acc["email"],
             "hp": hash_pw(acc["password"]), "role": acc["role"]},
        )
        id_map[acc["email"]] = uid
        print(f"  [ok]   {acc['email']}  ({acc['role']})  pw: {acc['password']}")
    await session.commit()
    return id_map


async def seed_courses(session, faculty_id):
    print("\n-- Courses --")
    for c in COURSES:
        r = await session.execute(
            text("SELECT id FROM courses WHERE title=:t AND is_deleted=false"), {"t": c["title"]}
        )
        if r.fetchone():
            print(f"  [skip] {c['title']} already exists")
            continue
        await session.execute(
            text("""
                INSERT INTO courses (id, title, description, price, is_free, faculty_id, is_deleted, created_at, updated_at)
                VALUES (:id, :title, :desc, :price, :free, :fid, false, NOW(), NOW())
            """),
            {"id": str(uuid.uuid4()), "title": c["title"], "desc": c["description"],
             "price": c["price"], "free": c["is_free"], "fid": faculty_id},
        )
        tag = "FREE" if c["is_free"] else f"Rs.{int(c['price'])}"
        print(f"  [ok]   {c['title']} [{tag}]")
    await session.commit()


async def seed_exams(session):
    print("\n-- Exams & Questions --")
    import json
    for exam_data in EXAMS:
        # Look up the course by title
        r = await session.execute(
            text("SELECT id FROM courses WHERE title=:t AND is_deleted=false"),
            {"t": exam_data["course_title"]},
        )
        course_row = r.fetchone()
        if not course_row:
            print(f"  [skip] Course '{exam_data['course_title']}' not found, skipping exam.")
            continue
        course_id = str(course_row[0])

        # Check if this exam already exists for the course
        r2 = await session.execute(
            text("SELECT id FROM exams WHERE title=:t AND course_id=:cid"),
            {"t": exam_data["title"], "cid": course_id},
        )
        existing_exam = r2.fetchone()
        if existing_exam:
            print(f"  [skip] Exam '{exam_data['title']}' already exists.")
            continue

        # Insert the exam
        exam_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO exams (id, course_id, title, duration_minutes, created_at, updated_at)
                VALUES (:id, :cid, :title, :dur, NOW(), NOW())
            """),
            {"id": exam_id, "cid": course_id, "title": exam_data["title"], "dur": exam_data["duration_minutes"]},
        )
        print(f"  [ok]   Exam: '{exam_data['title']}' ({exam_data['duration_minutes']} min)")

        # Insert each question
        for q in exam_data["questions"]:
            q_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO questions (id, exam_id, question_text, options, correct_answer, created_at, updated_at)
                    VALUES (:id, :eid, :qt, :opts::jsonb, :ca, NOW(), NOW())
                """),
                {
                    "id": q_id,
                    "eid": exam_id,
                    "qt": q["question_text"],
                    "opts": json.dumps(q["options"]),
                    "ca": q["correct_answer"],
                },
            )
            print(f"       + Q: {q['question_text'][:55]}...  [Ans: {q['correct_answer']}]")

    await session.commit()


async def main():
    print("=" * 50)
    print("  E-Learn Database Seeder")
    print("=" * 50)

    async with AsyncSessionLocal() as session:
        id_map = await seed_accounts(session)
        faculty_id = id_map.get("faculty@elearn.com")
        if not faculty_id:
            print("ERROR: faculty account not found, cannot seed courses.")
            return
        await seed_courses(session, faculty_id)
        await seed_exams(session)

    await engine.dispose()

    print("\n" + "=" * 50)
    print("  Done! Login credentials:")
    print("=" * 50)
    for acc in ACCOUNTS:
        print(f"  {acc['role']:<8}  {acc['email']:<26}  {acc['password']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
