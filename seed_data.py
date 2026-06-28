"""
seed_data.py - Seeds the database with richer demo data.

Accounts created:
  admin@elearn.com    / Admin@123     (admin)
  faculty@elearn.com  / Faculty@123   (faculty)
  teacher@elearn.com  / Teacher@123   (faculty)
  student@elearn.com  / Student@123   (student)

Data seeded:
  - Rich sample courses with thumbnail images
  - Course notes with content and file links
  - Multiple exams with questions
  - Direct conversations and messages

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

DB_HOST     = os.getenv("DB_HOST", "postgres.cds0wkgaawj8.ap-south-1.rds.amazonaws.com")
DB_PORT     = os.getenv("DB_PORT", "5432")
DB_NAME     = os.getenv("DB_NAME", "postgres")
DB_USER     = os.getenv("DB_USER", "elearn_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "findmeaA")
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
        "faculty_email": "faculty@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "title":       "Web Development with Flask",
        "description": "Build real-world web apps using Python and Flask. Includes REST APIs, SQLAlchemy and auth.",
        "price":       499.0,
        "is_free":     False,
        "faculty_email": "faculty@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "title":       "Cybersecurity Fundamentals",
        "description": "Master network security, ethical hacking, penetration testing and vulnerability assessment.",
        "price":       999.0,
        "is_free":     False,
        "faculty_email": "teacher@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "title":       "UI/UX Design Basics",
        "description": "Learn Figma, design principles, wireframing, prototyping and usability testing.",
        "price":       0.0,
        "is_free":     True,
        "faculty_email": "teacher@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1522542550221-31fd19575a2d?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "title":       "Business Analytics with Python",
        "description": "Use Python, Pandas and Matplotlib to analyse data, build dashboards and drive decisions.",
        "price":       799.0,
        "is_free":     False,
        "faculty_email": "faculty@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "title":       "SQL and Data Modeling",
        "description": "Design relational schemas, write efficient SQL queries, and understand indexing, joins and normalization.",
        "price":       349.0,
        "is_free":     False,
        "faculty_email": "teacher@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "title":       "Mobile App Design Sprint",
        "description": "Plan, prototype and validate a mobile app experience using research, flows, wireframes and quick usability loops.",
        "price":       0.0,
        "is_free":     True,
        "faculty_email": "teacher@elearn.com",
        "thumbnail_url": "https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?auto=format&fit=crop&w=1200&q=80",
    },
]

NOTES = [
    {
        "course_title": "Python for Beginners",
        "title": "Python Quick Revision Sheet",
        "content": "Covers variables, loops, functions, dictionaries, list comprehensions and common debugging tips for beginners.",
        "file_url": "https://example.com/notes/python-quick-revision.pdf",
        "file_type": "pdf",
        "uploaded_by_email": "faculty@elearn.com",
        "is_free": True,
    },
    {
        "course_title": "Python for Beginners",
        "title": "Practice Problems Pack",
        "content": "A set of starter practice questions around conditions, loops, functions and file handling.",
        "file_url": "https://example.com/notes/python-practice-pack.pdf",
        "file_type": "pdf",
        "uploaded_by_email": "faculty@elearn.com",
        "is_free": True,
    },
    {
        "course_title": "Web Development with Flask",
        "title": "Flask Routing and Templates",
        "content": "Explains Flask app structure, route handlers, Jinja templates and common layout patterns.",
        "file_url": "https://example.com/notes/flask-routing-guide.pdf",
        "file_type": "pdf",
        "uploaded_by_email": "faculty@elearn.com",
        "is_free": False,
    },
    {
        "course_title": "Cybersecurity Fundamentals",
        "title": "Recon and Threat Modeling Notes",
        "content": "Focuses on attack surfaces, recon workflow, common web vulnerabilities and reporting basics.",
        "file_url": "https://example.com/notes/cybersecurity-recon.docx",
        "file_type": "docx",
        "uploaded_by_email": "teacher@elearn.com",
        "is_free": False,
    },
    {
        "course_title": "UI/UX Design Basics",
        "title": "Figma Starter Checklist",
        "content": "Design system starter checklist covering spacing, color roles, typography and prototype review steps.",
        "file_url": "https://example.com/notes/figma-starter-checklist.pdf",
        "file_type": "pdf",
        "uploaded_by_email": "teacher@elearn.com",
        "is_free": True,
    },
    {
        "course_title": "Business Analytics with Python",
        "title": "Pandas Data Wrangling Cheatsheet",
        "content": "A compact guide to filtering, grouping, merging, missing value cleanup and quick chart creation in Pandas.",
        "file_url": "https://example.com/notes/pandas-cheatsheet.pdf",
        "file_type": "pdf",
        "uploaded_by_email": "faculty@elearn.com",
        "is_free": False,
    },
    {
        "course_title": "SQL and Data Modeling",
        "title": "Normalization and Query Patterns",
        "content": "Examples of one-to-many modeling, indexing, joins, aggregation and query tuning basics.",
        "file_url": "https://example.com/notes/sql-modeling-guide.pdf",
        "file_type": "pdf",
        "uploaded_by_email": "teacher@elearn.com",
        "is_free": False,
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
    {
        "course_title": "Web Development with Flask",
        "title": "Flask Fundamentals Assessment",
        "duration_minutes": 20,
        "questions": [
            {
                "question_text": "Which object is commonly used to define a Flask application instance?",
                "options": {"A": "FastAPI()", "B": "Flask(__name__)", "C": "App()", "D": "WSGI()"},
                "correct_answer": "B",
            },
            {
                "question_text": "What templating engine does Flask use by default?",
                "options": {"A": "Mako", "B": "Twig", "C": "Blade", "D": "Jinja2"},
                "correct_answer": "D",
            },
            {
                "question_text": "Which decorator is used to map a URL to a view function in Flask?",
                "options": {"A": "@app.route", "B": "@app.url", "C": "@flask.view", "D": "@route.bind"},
                "correct_answer": "A",
            },
            {
                "question_text": "What is `request.form` mainly used for?",
                "options": {"A": "Database migrations", "B": "Reading submitted form values", "C": "Serving static files", "D": "Creating sessions"},
                "correct_answer": "B",
            },
        ],
    },
    {
        "course_title": "Cybersecurity Fundamentals",
        "title": "Security Foundations Quiz",
        "duration_minutes": 25,
        "questions": [
            {
                "question_text": "Which principle gives users only the access required to do their job?",
                "options": {"A": "Fail open", "B": "Least privilege", "C": "Zero latency", "D": "Open trust"},
                "correct_answer": "B",
            },
            {
                "question_text": "What does CVE typically identify?",
                "options": {"A": "Encrypted backups", "B": "Known public vulnerabilities", "C": "Firewall rules", "D": "Private keys"},
                "correct_answer": "B",
            },
            {
                "question_text": "Which activity usually happens first in a penetration test?",
                "options": {"A": "Privilege escalation", "B": "Reconnaissance", "C": "Persistence", "D": "Exfiltration"},
                "correct_answer": "B",
            },
            {
                "question_text": "What is phishing primarily trying to obtain?",
                "options": {"A": "CPU cycles", "B": "Network bandwidth", "C": "Sensitive information or access", "D": "Source code formatting"},
                "correct_answer": "C",
            },
        ],
    },
    {
        "course_title": "UI/UX Design Basics",
        "title": "Design Principles Checkpoint",
        "duration_minutes": 15,
        "questions": [
            {
                "question_text": "Which principle helps users understand what elements belong together?",
                "options": {"A": "Proximity", "B": "Latency", "C": "Encryption", "D": "Pagination"},
                "correct_answer": "A",
            },
            {
                "question_text": "What is a wireframe mainly used for?",
                "options": {"A": "Database backup", "B": "Visual planning of layout and flow", "C": "Final branding export", "D": "Security testing"},
                "correct_answer": "B",
            },
            {
                "question_text": "Usability testing is most useful for:",
                "options": {"A": "Checking real user friction", "B": "Creating CSS variables", "C": "Compiling assets", "D": "Encrypting passwords"},
                "correct_answer": "A",
            },
        ],
    },
    {
        "course_title": "Business Analytics with Python",
        "title": "Analytics with Pandas Quiz",
        "duration_minutes": 20,
        "questions": [
            {
                "question_text": "Which Pandas method is commonly used to load CSV data?",
                "options": {"A": "pd.open_csv()", "B": "pd.read_csv()", "C": "pd.load_table()", "D": "pd.import_csv()"},
                "correct_answer": "B",
            },
            {
                "question_text": "What does `groupby()` help you do?",
                "options": {"A": "Encrypt files", "B": "Aggregate data by categories", "C": "Create APIs", "D": "Schedule jobs"},
                "correct_answer": "B",
            },
            {
                "question_text": "Which library is commonly paired with Pandas for plotting?",
                "options": {"A": "Matplotlib", "B": "Passlib", "C": "Asyncpg", "D": "Alembic"},
                "correct_answer": "A",
            },
        ],
    },
    {
        "course_title": "SQL and Data Modeling",
        "title": "SQL Core Concepts Test",
        "duration_minutes": 20,
        "questions": [
            {
                "question_text": "Which SQL clause is used to filter rows before aggregation?",
                "options": {"A": "HAVING", "B": "WHERE", "C": "ORDER BY", "D": "LIMIT"},
                "correct_answer": "B",
            },
            {
                "question_text": "What is normalization mainly intended to reduce?",
                "options": {"A": "Redundant data", "B": "Image size", "C": "CPU temperature", "D": "SSL latency"},
                "correct_answer": "A",
            },
            {
                "question_text": "Which join returns only rows with matches in both tables?",
                "options": {"A": "LEFT JOIN", "B": "RIGHT JOIN", "C": "INNER JOIN", "D": "FULL JOIN"},
                "correct_answer": "C",
            },
        ],
    },
]

MESSAGES = [
    {
        "participants": ["faculty@elearn.com", "student@elearn.com"],
        "items": [
            {
                "sender_email": "student@elearn.com",
                "message_type": "text",
                "content": "Hi ma'am, I just enrolled in Python for Beginners. Which note should I start with first?",
                "client_message_id": "seed-msg-python-1",
            },
            {
                "sender_email": "faculty@elearn.com",
                "message_type": "text",
                "content": "Start with the Python Quick Revision Sheet, then try the practice problems pack after lesson two.",
                "client_message_id": "seed-msg-python-2",
            },
            {
                "sender_email": "faculty@elearn.com",
                "message_type": "text_with_file",
                "content": "Sharing the revision PDF link here as well so you can reach it quickly.",
                "client_message_id": "seed-msg-python-3",
                "attachment": {
                    "original_filename": "python-quick-revision.pdf",
                    "storage_key": "seed/messages/python-quick-revision.pdf",
                    "mime_type": "application/pdf",
                    "file_extension": "pdf",
                    "file_size": 248320,
                    "checksum": "2e3f0ec0a2d1f2b1d1f84f03ea63d65ed84f53d6109824a6ea8b4952a3e5c111",
                },
            },
        ],
    },
    {
        "participants": ["teacher@elearn.com", "student@elearn.com"],
        "items": [
            {
                "sender_email": "teacher@elearn.com",
                "message_type": "text",
                "content": "The cybersecurity quiz opens this Friday. Review recon, common web risks and reporting terminology before attempting it.",
                "client_message_id": "seed-msg-cyber-1",
            },
            {
                "sender_email": "student@elearn.com",
                "message_type": "text",
                "content": "Understood. I finished the recon notes and will revise CVE and least-privilege topics tonight.",
                "client_message_id": "seed-msg-cyber-2",
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


async def seed_courses(session, user_ids):
    print("\n-- Courses --")
    for c in COURSES:
        faculty_id = user_ids.get(c["faculty_email"])
        if not faculty_id:
            print(f"  [skip] Faculty '{c['faculty_email']}' not found for {c['title']}")
            continue
        r = await session.execute(
            text("SELECT id FROM courses WHERE title=:t AND is_deleted=false"), {"t": c["title"]}
        )
        existing_row = r.fetchone()
        if existing_row:
            await session.execute(
                text("""
                    UPDATE courses
                    SET description=:desc,
                        price=:price,
                        is_free=:free,
                        faculty_id=:fid,
                        thumbnail_url=:thumb,
                        updated_at=NOW()
                    WHERE id=:id
                """),
                {
                    "id": str(existing_row[0]),
                    "desc": c["description"],
                    "price": c["price"],
                    "free": c["is_free"],
                    "fid": faculty_id,
                    "thumb": c["thumbnail_url"],
                },
            )
            print(f"  [sync] {c['title']}")
            continue
        await session.execute(
            text("""
                INSERT INTO courses (id, title, description, price, is_free, faculty_id, thumbnail_url, is_deleted, created_at, updated_at)
                VALUES (:id, :title, :desc, :price, :free, :fid, :thumb, false, NOW(), NOW())
            """),
            {"id": str(uuid.uuid4()), "title": c["title"], "desc": c["description"],
             "price": c["price"], "free": c["is_free"], "fid": faculty_id, "thumb": c["thumbnail_url"]},
        )
        tag = "FREE" if c["is_free"] else f"Rs.{int(c['price'])}"
        print(f"  [ok]   {c['title']} [{tag}]")
    await session.commit()


async def get_course_ids(session):
    rows = await session.execute(text("SELECT id, title FROM courses WHERE is_deleted=false"))
    return {title: str(course_id) for course_id, title in rows.fetchall()}


async def seed_notes(session, course_ids, user_ids):
    print("\n-- Notes --")
    for note in NOTES:
        course_id = course_ids.get(note["course_title"])
        uploader_id = user_ids.get(note["uploaded_by_email"])
        if not course_id or not uploader_id:
            print(f"  [skip] Note '{note['title']}' missing course or uploader")
            continue

        existing = await session.execute(
            text("SELECT id FROM notes WHERE course_id=:cid AND title=:title"),
            {"cid": course_id, "title": note["title"]},
        )
        row = existing.fetchone()

        params = {
            "cid": course_id,
            "title": note["title"],
            "content": note["content"],
            "file_url": note["file_url"],
            "file_type": note["file_type"],
            "uploaded_by": uploader_id,
            "is_free": note["is_free"],
        }

        if row:
            await session.execute(
                text("""
                    UPDATE notes
                    SET content=:content,
                        file_url=:file_url,
                        file_type=:file_type,
                        uploaded_by=:uploaded_by,
                        is_free=:is_free,
                        updated_at=NOW()
                    WHERE id=:id
                """),
                {"id": str(row[0]), **params},
            )
            print(f"  [sync] {note['title']}")
            continue

        await session.execute(
            text("""
                INSERT INTO notes (id, course_id, title, content, file_url, file_type, uploaded_by, is_free, created_at, updated_at)
                VALUES (:id, :cid, :title, :content, :file_url, :file_type, :uploaded_by, :is_free, NOW(), NOW())
            """),
            {"id": str(uuid.uuid4()), **params},
        )
        print(f"  [ok]   {note['title']}")

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


def normalize_pair(user_a, user_b):
    a_uuid = uuid.UUID(str(user_a))
    b_uuid = uuid.UUID(str(user_b))
    return (str(a_uuid), str(b_uuid)) if a_uuid < b_uuid else (str(b_uuid), str(a_uuid))


async def seed_messages(session, user_ids):
    print("\n-- Messages --")
    for convo in MESSAGES:
        participant_ids = [user_ids.get(email) for email in convo["participants"]]
        if any(pid is None for pid in participant_ids):
            print(f"  [skip] Conversation participants missing: {', '.join(convo['participants'])}")
            continue

        participant_one_id, participant_two_id = normalize_pair(participant_ids[0], participant_ids[1])
        existing = await session.execute(
            text("""
                SELECT id FROM direct_conversations
                WHERE participant_one_id=:p1 AND participant_two_id=:p2
            """),
            {"p1": participant_one_id, "p2": participant_two_id},
        )
        conversation_row = existing.fetchone()

        if conversation_row:
            conversation_id = str(conversation_row[0])
        else:
            conversation_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO direct_conversations (id, participant_one_id, participant_two_id, created_at, updated_at)
                    VALUES (:id, :p1, :p2, NOW(), NOW())
                """),
                {"id": conversation_id, "p1": participant_one_id, "p2": participant_two_id},
            )
            print(f"  [ok]   Conversation {convo['participants'][0]} <-> {convo['participants'][1]}")

        last_message_id = None

        for item in convo["items"]:
            sender_id = user_ids.get(item["sender_email"])
            if not sender_id:
                continue

            existing_message = await session.execute(
                text("""
                    SELECT id FROM messages
                    WHERE sender_id=:sender_id AND client_message_id=:client_message_id
                """),
                {"sender_id": sender_id, "client_message_id": item["client_message_id"]},
            )
            message_row = existing_message.fetchone()

            if message_row:
                last_message_id = str(message_row[0])
                print(f"  [skip] Message {item['client_message_id']} already exists")
                continue

            message_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO messages (
                        id, conversation_id, sender_id, message_type, content, client_message_id,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :conversation_id, :sender_id, :message_type, :content, :client_message_id,
                        NOW(), NOW()
                    )
                """),
                {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "sender_id": sender_id,
                    "message_type": item["message_type"],
                    "content": item.get("content"),
                    "client_message_id": item["client_message_id"],
                },
            )

            attachment = item.get("attachment")
            if attachment:
                await session.execute(
                    text("""
                        INSERT INTO message_attachments (
                            id, message_id, original_filename, storage_key, mime_type,
                            file_extension, file_size, checksum, scan_status, created_at
                        )
                        VALUES (
                            :id, :message_id, :original_filename, :storage_key, :mime_type,
                            :file_extension, :file_size, :checksum, 'clean', NOW()
                        )
                    """),
                    {"id": str(uuid.uuid4()), "message_id": message_id, **attachment},
                )

            last_message_id = message_id
            print(f"  [ok]   Message {item['client_message_id']}")

        if last_message_id:
            await session.execute(
                text("""
                    UPDATE direct_conversations
                    SET last_message_id=:last_message_id,
                        updated_at=NOW()
                    WHERE id=:conversation_id
                """),
                {"conversation_id": conversation_id, "last_message_id": last_message_id},
            )

            for participant_id in (participant_one_id, participant_two_id):
                await session.execute(
                    text("""
                        INSERT INTO conversation_read_states (conversation_id, user_id, last_read_message_id, last_read_at)
                        VALUES (:conversation_id, :user_id, :last_read_message_id, NOW())
                        ON CONFLICT (conversation_id, user_id)
                        DO UPDATE SET
                            last_read_message_id=EXCLUDED.last_read_message_id,
                            last_read_at=EXCLUDED.last_read_at
                    """),
                    {
                        "conversation_id": conversation_id,
                        "user_id": participant_id,
                        "last_read_message_id": last_message_id,
                    },
                )

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
        await seed_courses(session, id_map)
        course_ids = await get_course_ids(session)
        await seed_notes(session, course_ids, id_map)
        await seed_exams(session)
        await seed_messages(session, id_map)

    await engine.dispose()

    print("\n" + "=" * 50)
    print("  Done! Login credentials:")
    print("=" * 50)
    for acc in ACCOUNTS:
        print(f"  {acc['role']:<8}  {acc['email']:<26}  {acc['password']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
