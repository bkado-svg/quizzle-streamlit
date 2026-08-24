import hashlib
import io
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from streamlit_autorefresh import st_autorefresh

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("QUIZZLE_DB_PATH", ROOT / "quizzle.db"))
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)

COURSE_CATALOG = {
    "Computer Science": {
        "100": ["CSC 101 · Introduction to Computer Science", "CSC 102 · Introduction to Programming", "MTH 101 · Elementary Mathematics I"],
        "200": ["CSC 201 · Computer Programming I", "CSC 202 · Data Structures and Algorithms", "CSC 203 · Computer Architecture"],
        "300": ["CSC 301 · Operating Systems", "CSC 302 · Database Systems", "CSC 303 · Software Engineering"],
        "400": ["CSC 401 · Artificial Intelligence", "CSC 402 · Computer Networks", "CSC 403 · Final Year Project"],
        "500": ["CSC 501 · Advanced Algorithms", "CSC 502 · Machine Learning", "CSC 503 · Research Methods"],
        "Postgraduate": ["CSC 701 · Advanced Computing", "CSC 702 · Data Science", "CSC 703 · Graduate Seminar"],
    },
    "Education": {
        "100": ["EDU 101 · Introduction to Education", "EDU 102 · Foundations of Teaching"],
        "200": ["EDU 201 · Educational Psychology", "EDU 202 · Curriculum Studies"],
        "300": ["EDU 301 · Measurement and Evaluation", "EDU 302 · Teaching Practice"],
        "400": ["EDU 401 · Educational Management", "EDU 402 · Research Project"],
        "500": ["EDU 501 · Advanced Curriculum Theory"],
        "Postgraduate": ["EDU 701 · Advanced Educational Research", "EDU 702 · Policy and Leadership"],
    },
    "Business Administration": {
        "100": ["BUS 101 · Introduction to Business", "ACC 101 · Principles of Accounting"],
        "200": ["BUS 201 · Organisational Behaviour", "MKT 201 · Principles of Marketing"],
        "300": ["BUS 301 · Operations Management", "FIN 301 · Business Finance"],
        "400": ["BUS 401 · Strategic Management", "BUS 402 · Entrepreneurship"],
        "500": ["BUS 501 · Advanced Management"],
        "Postgraduate": ["BUS 701 · Corporate Strategy", "BUS 702 · Graduate Research Seminar"],
    },
    "Mass Communication": {
        "100": ["MAC 101 · Introduction to Mass Communication", "MAC 102 · Writing for the Media"],
        "200": ["MAC 201 · News Reporting", "MAC 202 · Broadcast Production"],
        "300": ["MAC 301 · Media Law and Ethics", "MAC 302 · Public Relations"],
        "400": ["MAC 401 · Communication Research", "MAC 402 · Media Project"],
        "500": ["MAC 501 · Advanced Media Studies"],
        "Postgraduate": ["MAC 701 · Communication Theory", "MAC 702 · Digital Media Research"],
    },
}

st.set_page_config(page_title="Quizzle", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

:root {
  --ink: #15243b;
  --muted: #64748b;
  --brand: #5b4bea;
  --brand-dark: #4033c8;
  --mint: #21bfa6;
  --surface: #ffffff;
  --line: #e7eaf3;
}

html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: "DM Sans", ui-sans-serif, system-ui, sans-serif;
  color: var(--ink);
}

[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 90% -10%, rgba(91,75,234,.12), transparent 32rem),
    radial-gradient(circle at 5% 100%, rgba(33,191,166,.09), transparent 28rem),
    #f7f8fc;
}

/* Hide Streamlit's hosted-app chrome (Share/Fork/Deploy and hosting badge). */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stFooter"],
#MainMenu,
footer,
.viewerBadge_container__1QSob { display: none !important; }
[data-testid="stAppViewContainer"] > .main { padding-top: 0 !important; }

[data-testid="stMainBlockContainer"] { max-width: 1240px; padding: 2.2rem 3rem 4rem; }
h1, h2, h3 { font-family: "Manrope", sans-serif !important; color: var(--ink); letter-spacing: -.035em; }
h2 { font-size: 2rem !important; font-weight: 800 !important; margin-bottom: .1rem !important; }
h3 { font-size: 1.16rem !important; font-weight: 700 !important; margin-top: 1.8rem !important; }
p, label, .stCaption { letter-spacing: -.005em; }
[data-testid="stMain"] label, [data-testid="stMain"] [data-testid="stMarkdownContainer"] p { color: var(--ink); }
[data-testid="stMain"] .stCaption { color: var(--muted) !important; }

[data-testid="stSidebar"] {
  background: linear-gradient(165deg, #18233e 0%, #29215d 72%, #4033c8 140%);
  border-right: 0;
}
[data-testid="stSidebar"] * { color: #f8fafc !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #cbd3e8 !important; }
[data-testid="stSidebar"] h1 { font-size: 1.45rem !important; letter-spacing: -.03em; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .3rem; }
[data-testid="stSidebar"] label[data-baseweb="radio"] {
  padding: .62rem .75rem; border-radius: .72rem; transition: .18s ease;
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover { background: rgba(255,255,255,.09); }
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
  background: rgba(255,255,255,.14); box-shadow: inset 3px 0 #5eead4;
}
[data-testid="stSidebar"] .stButton button {
  background: rgba(255,255,255,.08) !important; border-color: rgba(255,255,255,.15) !important;
}

[data-testid="stMetric"] {
  background: rgba(255,255,255,.9); border: 1px solid var(--line); border-radius: 1rem;
  padding: 1rem 1.15rem; box-shadow: 0 8px 26px rgba(32,40,80,.06);
}
[data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
[data-testid="stMetricValue"] { color: var(--ink); font-family: "Manrope"; font-weight: 800; }

.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button, a[data-testid="stLinkButton"] {
  border-radius: .72rem !important; min-height: 2.7rem; border: 1px solid #dfe3ee !important;
  font-weight: 700 !important; box-shadow: 0 3px 10px rgba(34,42,80,.05); transition: .18s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  border-color: var(--brand) !important; color: var(--brand) !important; transform: translateY(-1px);
}
[data-testid="stFormSubmitButton"] > button, button[kind="primary"] {
  background: linear-gradient(135deg, var(--brand), var(--brand-dark)) !important;
  color: white !important; border: 0 !important;
}
[data-testid="stFormSubmitButton"] > button:hover { color: white !important; box-shadow: 0 8px 18px rgba(91,75,234,.24); }
[data-testid="stFormSubmitButton"] > button p { color: white !important; }

[data-testid="stForm"], [data-testid="stExpander"], [data-testid="stDataFrame"], [data-testid="stAlert"] {
  border-radius: 1rem !important; border-color: var(--line) !important;
  box-shadow: 0 8px 28px rgba(32,40,80,.055); overflow: hidden;
}
[data-testid="stForm"], [data-testid="stExpander"] { background: rgba(255,255,255,.86); }
[data-testid="stExpander"] details summary { padding: .9rem 1rem; font-weight: 700; }

input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] {
  border-radius: .66rem !important; border: 1px solid #dfe3ee !important; background: #fff !important;
}
input:focus, textarea:focus { box-shadow: 0 0 0 3px rgba(91,75,234,.12) !important; }
[data-baseweb="tab-list"] { gap: .45rem; border-bottom: 1px solid var(--line); }
[data-baseweb="tab"] { border-radius: .7rem .7rem 0 0; padding: .7rem 1.1rem; font-weight: 700; }
[aria-selected="true"][data-baseweb="tab"] { color: var(--brand); background: rgba(91,75,234,.07); }

.qz-hero {
  padding: 1.35rem 1.5rem; margin: .15rem 0 1.35rem; border-radius: 1.15rem;
  background: linear-gradient(120deg, #ffffff 0%, #f0efff 100%); border: 1px solid #e5e2ff;
  box-shadow: 0 10px 32px rgba(59,50,140,.07);
}
.qz-hero h2 { margin: 0 !important; }
.qz-hero p { margin: .35rem 0 0; color: var(--muted); }
.qz-original-hero {
  position: fixed; z-index: 2; inset: 0 50% 0 0; padding: clamp(4rem, 12vh, 9rem) clamp(3rem, 7vw, 7rem);
  display: flex; flex-direction: column; justify-content: center; color: white;
  background:
    radial-gradient(circle at 85% 80%, rgba(122,109,255,.6), transparent 42%),
    linear-gradient(145deg, #26205d 0%, #373395 58%, #5c55d9 100%);
}
.qz-original-brand { position: absolute; top: 10vh; display: flex; align-items: center; gap: .7rem; font: 800 1.35rem "Manrope"; }
.qz-original-mark { display: inline-grid; place-items: center; width: 2rem; height: 2rem; border-radius: .55rem; background: #665cf0; box-shadow: 0 8px 20px rgba(0,0,0,.18); }
.qz-original-kicker { font-size: .68rem; font-weight: 700; letter-spacing: .28em; opacity: .8; }
.qz-original-hero h1 { color: white; font-size: clamp(2.45rem, 4vw, 4rem); line-height: 1.08; font-weight: 500; margin: 1.35rem 0 1rem; max-width: 34rem; }
.qz-original-copy { color: rgba(255,255,255,.72) !important; max-width: 34rem; line-height: 1.7; }
.qz-original-stats { display: flex; gap: clamp(2rem,4vw,4.5rem); margin-top: 2rem; }
.qz-original-stats strong { display: block; font: 700 1.05rem "Manrope"; }
.qz-original-stats span { display: block; margin-top: .35rem; font-size: .68rem; opacity: .62; }
.qz-form-heading h2 { font-size: 1.55rem !important; margin: .5rem 0 .15rem !important; }
.qz-form-heading p { color: var(--muted) !important; margin: 0 0 1.2rem; }
body:has(.qz-original-hero) [data-testid="stMainBlockContainer"] { max-width: none; padding: 8vh 6vw 4rem calc(50% + 6vw); }
body:has(.qz-original-hero) [data-testid="stTabs"] { max-width: 430px; margin: auto; padding: 2rem; border: 1px solid var(--line); border-radius: 1.25rem; background: rgba(255,255,255,.94); box-shadow: 0 18px 50px rgba(38,32,93,.12); }
body:has(.qz-original-hero) [data-baseweb="tab-list"] { padding: .25rem; border: 0; border-radius: .75rem; background: #f0f1f6; }
body:has(.qz-original-hero) [data-baseweb="tab"] { flex: 1; justify-content: center; border-radius: .58rem; }
body:has(.qz-original-hero) [aria-selected="true"][data-baseweb="tab"] { background: white; box-shadow: 0 3px 10px rgba(30,35,70,.09); }
body:has(.qz-original-hero) [data-testid="stTabs"] [data-testid="stForm"] { padding: 0; border: 0 !important; background: transparent; box-shadow: none; }
code { border-radius: .55rem !important; color: var(--brand-dark) !important; background: #eeecff !important; }
hr { border-color: var(--line) !important; }
@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem 3rem; }
  .qz-hero { padding: 1rem; }
  .qz-original-hero { display: none; }
  body:has(.qz-original-hero) [data-testid="stMainBlockContainer"] { padding: 2.5rem 1rem; }
  body:has(.qz-original-hero) [data-testid="stTabs"] { padding: 1.25rem; }
}
</style>
""", unsafe_allow_html=True)


def db():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def password_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, role TEXT NOT NULL, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, name TEXT NOT NULL, level TEXT, session TEXT, course TEXT, join_code TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(teacher_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL, name TEXT NOT NULL, student_number TEXT, phone TEXT, email TEXT, UNIQUE(class_id,student_number), FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS quizzes(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, class_id INTEGER NOT NULL, title TEXT NOT NULL, status TEXT DEFAULT 'Draft', share_code TEXT UNIQUE NOT NULL, time_limit INTEGER DEFAULT 30, show_results INTEGER DEFAULT 1, created_at TEXT NOT NULL, FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY, quiz_id INTEGER NOT NULL, prompt TEXT NOT NULL, question_type TEXT DEFAULT 'Multiple choice', options_json TEXT DEFAULT '[]', correct_answer TEXT, points REAL DEFAULT 1, FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, quiz_id INTEGER NOT NULL, student_id INTEGER NOT NULL, status TEXT DEFAULT 'in_progress', started_at TEXT NOT NULL, submitted_at TEXT, score REAL DEFAULT 0, max_score REAL DEFAULT 0, answers_json TEXT DEFAULT '{}', last_seen TEXT, UNIQUE(quiz_id,student_id,status), FOREIGN KEY(quiz_id) REFERENCES quizzes(id), FOREIGN KEY(student_id) REFERENCES students(id));
    CREATE TABLE IF NOT EXISTS activity_events(id INTEGER PRIMARY KEY, attempt_id INTEGER NOT NULL, event_type TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, duration_seconds INTEGER DEFAULT 0, FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS resources(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL, class_id INTEGER NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL, location TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE);
    """)
    existing_columns = {item[1] for item in con.execute("PRAGMA table_info(users)").fetchall()}
    for column in ("university_type", "university", "faculty", "department"):
        if column not in existing_columns:
            con.execute(f"ALTER TABLE users ADD COLUMN {column} TEXT")
    for role, name, email, password in [("admin", "Quizzle Administrator", "admin@quizzle.app", "Admin123!"), ("teacher", "Demo Teacher", "teacher@quizzle.app", "Teacher123!")]:
        con.execute("INSERT OR IGNORE INTO users(role,name,email,password_hash) VALUES(?,?,?,?)", (role, name, email, password_hash(password)))
    con.execute("UPDATE users SET department='Computer Science' WHERE email='teacher@quizzle.app' AND (department IS NULL OR department='')")
    con.commit(); con.close()


def rows(sql, params=()):
    con = db(); result = [dict(row) for row in con.execute(sql, params).fetchall()]; con.close(); return result


def run(sql, params=()):
    con = db(); cursor = con.execute(sql, params); con.commit(); value = cursor.lastrowid; con.close(); return value


def code(prefix="QZ"):
    return f"{prefix}{int(time.time()*1000)%1000000:06d}"


def title(text, caption=None):
    subtitle = f"<p>{caption}</p>" if caption else ""
    st.markdown(f'<section class="qz-hero"><h2>{text}</h2>{subtitle}</section>', unsafe_allow_html=True)


def logout():
    st.session_state.clear(); st.rerun()


def login():
    st.markdown("""
    <section class="qz-original-hero">
      <div class="qz-original-brand"><span class="qz-original-mark">Q</span> Quizzle</div>
      <div class="qz-original-kicker">TEACH • ASSESS • IMPROVE</div>
      <h1>One secure doorway for every classroom.</h1>
      <p class="qz-original-copy">Teachers build assessments, monitor activity and turn every result into a clear teaching decision.</p>
      <div class="qz-original-stats">
        <div><strong>3</strong><span>university types</span></div>
        <div><strong>Linked</strong><span>academic units</span></div>
        <div><strong>Verified</strong><span>teacher accounts</span></div>
      </div>
    </section>
    """, unsafe_allow_html=True)
    teacher, student, admin = st.tabs(["Teacher", "Student", "Admin"])
    with teacher:
        st.markdown('<div class="qz-form-heading"><h2>Teacher sign in</h2><p>Use your official institutional email.</p></div>', unsafe_allow_html=True)
        with st.form("teacher_login"):
            email = st.text_input("Official institutional email", key="te"); password = st.text_input("Password", type="password", key="tp")
            if st.form_submit_button("Continue", use_container_width=True): authenticate(email, password, "teacher")
        with st.expander("Create teacher account"):
            with st.form("register"):
                name=st.text_input("Full name"); email=st.text_input("Institutional email"); password=st.text_input("Create password",type="password")
                university_type=st.selectbox("University type",["Federal","State","Private"]); university=st.text_input("University"); faculty=st.text_input("Faculty"); department=st.text_input("Department")
                if st.form_submit_button("Create account"):
                    try: run("INSERT INTO users(role,name,email,password_hash,university_type,university,faculty,department) VALUES('teacher',?,?,?,?,?,?,?)",(name,email.lower(),password_hash(password),university_type,university,faculty,department)); st.success("Account created. Please sign in.")
                    except sqlite3.IntegrityError: st.error("That email is already registered.")
    with student:
        st.markdown('<div class="qz-form-heading"><h2>Student access</h2><p>Enter your class or live quiz code.</p></div>', unsafe_allow_html=True)
        with st.form("student_login"):
            join=st.text_input("Class or quiz code").strip().upper(); number=st.text_input("Student number").strip(); name=st.text_input("Full name")
            if st.form_submit_button("Open class",use_container_width=True): student_signin(join,number,name)
    with admin:
        st.markdown('<div class="qz-form-heading"><h2>Admin sign in</h2><p>Access account and platform controls.</p></div>', unsafe_allow_html=True)
        with st.form("admin_login"):
            email=st.text_input("Admin email"); password=st.text_input("Admin password",type="password")
            if st.form_submit_button("Sign in as admin",use_container_width=True): authenticate(email,password,"admin")


def authenticate(email,password,role):
    found=rows("SELECT * FROM users WHERE lower(email)=? AND password_hash=? AND role=? AND active=1",(email.lower(),password_hash(password),role))
    if not found: st.error("Invalid sign-in details."); return
    st.session_state.update(role=role,user=found[0]); st.rerun()


def student_signin(join,number,name):
    classes=rows("SELECT * FROM classes WHERE join_code=?",(join,)); quizzes=rows("SELECT * FROM quizzes WHERE share_code=? AND status='Live'",(join,))
    class_id=classes[0]["id"] if classes else quizzes[0]["class_id"] if quizzes else None
    if not class_id: st.error("Code not found or quiz is not live."); return
    found=rows("SELECT * FROM students WHERE class_id=? AND student_number=?",(class_id,number))
    if found: student=found[0]
    else:
        sid=run("INSERT INTO students(class_id,name,student_number) VALUES(?,?,?)",(class_id,name or number,number)); student=rows("SELECT * FROM students WHERE id=?",(sid,))[0]
    st.session_state.update(role="student",student=student,class_id=class_id,direct_quiz=quizzes[0]["id"] if quizzes else None); st.rerun()


def teacher_app():
    user=st.session_state.user
    with st.sidebar:
        st.title("Q · Quizzle"); page=st.radio("Workspace",["Overview","Courses","My quizzes","Monitoring","Reports","Results","Resources"]); st.caption(user["name"]); st.button("Sign out",on_click=logout)
    if page=="Overview": teacher_overview(user)
    elif page=="Courses": courses_page(user)
    elif page=="My quizzes": quizzes_page(user)
    elif page=="Monitoring": monitoring_page(user)
    elif page=="Reports": reports_page(user)
    elif page=="Results": results_page(user)
    else: resources_page(user)


def teacher_overview(user):
    title("Overview","Live summary of teaching activity")
    cs=rows("SELECT * FROM classes WHERE teacher_id=?",(user["id"],)); qs=rows("SELECT * FROM quizzes WHERE teacher_id=?",(user["id"],)); reports=teacher_attempts(user["id"])
    a,b,c,d=st.columns(4); a.metric("Courses",len(cs)); b.metric("Quizzes",len(qs)); c.metric("Submissions",sum(x["status"]=="submitted" for x in reports)); d.metric("Activity alerts",sum(x["alert_count"] for x in reports))
    st.subheader("Recent activity"); st.dataframe(pd.DataFrame(reports[:10]) if reports else pd.DataFrame(columns=["student","quiz","status"]),use_container_width=True,hide_index=True)


def department_catalog(department, level):
    department = (department or "").strip().lower()
    matched = next((name for name in COURSE_CATALOG if name.lower() == department or name.lower() in department or department in name.lower()), None)
    return COURSE_CATALOG.get(matched, {}).get(level, []) if matched else []


def courses_page(user):
    department = user.get("department") or "Not configured"
    title("Courses", f"Courses for {department} are organised by level and academic session")
    with st.expander("Add course",expanded=not rows("SELECT id FROM classes WHERE teacher_id=?",(user["id"],))):
        with st.form("new_class"):
            level=st.selectbox("Level",["100","200","300","400","500","Postgraduate"])
            available=department_catalog(department,level)
            if available:
                course=st.selectbox("Department course",available,help=f"Automatically populated from the {department} course catalogue")
            else:
                st.warning(f"No course catalogue is currently available for {department} at {level} level. Ask an administrator to add it.")
                course=None
            name=st.text_input("Course group / class name",placeholder="e.g. Computer Science 200L")
            session=st.text_input("Academic session",f"{datetime.now().year-1}/{str(datetime.now().year)[-2:]}")
            if st.form_submit_button("Add course",disabled=not available):
                run("INSERT INTO classes(teacher_id,name,level,session,course,join_code,created_at) VALUES(?,?,?,?,?,?,?)",(user["id"],name,level,session,course,code("CL"),now_iso())); st.rerun()
    for cls in rows("SELECT * FROM classes WHERE teacher_id=? ORDER BY session DESC,level,name",(user["id"],)):
        with st.expander(f"{cls['level']} · {cls['name']} — {cls['course']}"):
            st.code(cls["join_code"]); roster=rows("SELECT * FROM students WHERE class_id=?",(cls["id"],)); st.dataframe(roster,use_container_width=True,hide_index=True)
            upload=st.file_uploader("Replace/upload student list (CSV)",type=["csv"],key=f"roster{cls['id']}")
            if upload:
                frame=pd.read_csv(upload)
                for _,item in frame.iterrows(): run("INSERT OR REPLACE INTO students(class_id,name,student_number,email,phone) VALUES(?,?,?,?,?)",(cls["id"],str(item.get("name","")),str(item.get("student_number","")),str(item.get("email","")),str(item.get("phone",""))))
                st.success("Roster uploaded.")


def quizzes_page(user):
    title("My quizzes","Create, edit, copy, share, open, close, and delete quizzes")
    classes=rows("SELECT * FROM classes WHERE teacher_id=?",(user["id"],)); labels={f"{c['level']} · {c['name']} · {c['course']}":c["id"] for c in classes}
    if labels:
        with st.expander("Create quiz"):
            with st.form("new_quiz"):
                cls=st.selectbox("Class and course",labels); name=st.text_input("Quiz title"); limit=st.number_input("Time limit (minutes)",1,300,30); show=st.checkbox("Students can see reviewed answers",True)
                if st.form_submit_button("Create"):
                    run("INSERT INTO quizzes(teacher_id,class_id,title,share_code,time_limit,show_results,created_at) VALUES(?,?,?,?,?,?,?)",(user["id"],labels[cls],name,code(),limit,int(show),now_iso())); st.rerun()
    for quiz in rows("SELECT q.*,c.name class_name,c.course FROM quizzes q JOIN classes c ON c.id=q.class_id WHERE q.teacher_id=? ORDER BY q.id DESC",(user["id"],)):
        with st.expander(f"{quiz['status']} · {quiz['title']} — {quiz['class_name']}"):
            st.code(quiz["share_code"]); st.caption("Share code remains available while live or closed.")
            questions=rows("SELECT * FROM questions WHERE quiz_id=?",(quiz["id"],)); st.dataframe(pd.DataFrame(questions),use_container_width=True,hide_index=True)
            with st.form(f"question{quiz['id']}"):
                qtype=st.selectbox("Question type",["Multiple choice","Open ended"],key=f"qt{quiz['id']}"); prompt=st.text_area("Question"); options=st.text_area("Options, one per line") if qtype=="Multiple choice" else ""; answer=st.text_input("Correct answer"); points=st.number_input("Points",0.5,100.0,1.0,0.5)
                if st.form_submit_button("Add question"):
                    run("INSERT INTO questions(quiz_id,prompt,question_type,options_json,correct_answer,points) VALUES(?,?,?,?,?,?)",(quiz["id"],prompt,qtype,json.dumps([x.strip() for x in options.splitlines() if x.strip()]),answer,points)); st.rerun()
            c1,c2,c3,c4=st.columns(4)
            if c1.button("Go live",key=f"live{quiz['id']}"): run("UPDATE quizzes SET status='Live' WHERE id=?",(quiz["id"],)); st.rerun()
            if c2.button("Close",key=f"close{quiz['id']}"): run("UPDATE quizzes SET status='Closed' WHERE id=?",(quiz["id"],)); st.rerun()
            if c3.button("Copy",key=f"copy{quiz['id']}"):
                new=run("INSERT INTO quizzes(teacher_id,class_id,title,status,share_code,time_limit,show_results,created_at) VALUES(?,?,?,'Draft',?,?,?,?)",(user["id"],quiz["class_id"],quiz["title"]+" (Copy)",code(),quiz["time_limit"],quiz["show_results"],now_iso()))
                for q in questions: run("INSERT INTO questions(quiz_id,prompt,question_type,options_json,correct_answer,points) VALUES(?,?,?,?,?,?)",(new,q["prompt"],q["question_type"],q["options_json"],q["correct_answer"],q["points"])); st.rerun()
            if c4.button("Delete",key=f"delete{quiz['id']}"): run("DELETE FROM quizzes WHERE id=?",(quiz["id"],)); st.rerun()


def teacher_attempts(teacher_id):
    data=rows("""SELECT a.*,s.name student,s.student_number,q.title quiz,c.name class_name,c.level,c.session,c.course FROM attempts a JOIN students s ON s.id=a.student_id JOIN quizzes q ON q.id=a.quiz_id JOIN classes c ON c.id=q.class_id WHERE q.teacher_id=? ORDER BY a.started_at DESC""",(teacher_id,))
    for item in data:
        events=rows("SELECT * FROM activity_events WHERE attempt_id=? ORDER BY started_at",(item["id"],)); item["alert_count"]=len(events); item["activity_details"]="; ".join(f"{e['event_type']} ({e['duration_seconds']}s)" for e in events) or "Clear"
    return data


def monitoring_page(user):
    st_autorefresh(interval=2000,key="monitor_refresh"); title("Live monitoring","Students disappear after submission; activity refreshes every two seconds")
    live=[x for x in teacher_attempts(user["id"]) if x["status"]=="in_progress"]
    now=datetime.now(timezone.utc)
    for item in live:
        last=datetime.fromisoformat(item["last_seen"] or item["started_at"]); gap=int((now-last).total_seconds())
        if gap>=15 and not rows("SELECT id FROM activity_events WHERE attempt_id=? AND event_type='Page hidden' AND ended_at IS NULL",(item["id"],)):
            run("INSERT INTO activity_events(attempt_id,event_type,started_at,duration_seconds) VALUES(?,?,?,?)",(item["id"],"Page hidden",item["last_seen"] or item["started_at"],gap))
    frame=pd.DataFrame(live); st.dataframe(frame[[x for x in ["student","student_number","quiz","class_name","started_at","last_seen","alert_count","activity_details"] if x in frame.columns]] if not frame.empty else frame,use_container_width=True,hide_index=True)


def report_frame(user):
    data=teacher_attempts(user["id"]); return pd.DataFrame(data)


def reports_page(user):
    title("Reports","Select a quiz to view teaching insights and activity records")
    frame=report_frame(user)
    if frame.empty: st.info("No attempts recorded."); return
    quiz=st.selectbox("Quiz",sorted(frame.quiz.unique())); selected=frame[frame.quiz==quiz].copy(); st.dataframe(selected,use_container_width=True,hide_index=True)
    completed=selected[selected.status=="submitted"]; a,b,c=st.columns(3); a.metric("Attempts",len(selected)); b.metric("Average",f"{completed.score.mean():.1f}" if len(completed) else "—"); c.metric("Flagged",int((selected.alert_count>0).sum()))
    excel=io.BytesIO(); selected.to_excel(excel,index=False,engine="openpyxl"); st.download_button("Download Excel",excel.getvalue(),f"{quiz}-report.xlsx")
    st.download_button("Download PDF",pdf_report(selected,quiz),f"{quiz}-report.pdf",mime="application/pdf")


def pdf_report(frame,title_text):
    output=io.BytesIO(); doc=SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=12*mm,rightMargin=12*mm); styles=getSampleStyleSheet(); content=[Paragraph("QUIZZLE ASSESSMENT REPORT",styles["Title"]),Paragraph(title_text,styles["Heading2"]),Spacer(1,8)]
    columns=[x for x in ["student","student_number","started_at","submitted_at","score","alert_count","activity_details"] if x in frame.columns]; values=[columns]+[[str(row.get(c,"")) for c in columns] for _,row in frame.iterrows()]; table=Table(values,repeatRows=1); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#635bdf")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")])); content.append(table); doc.build(content); return output.getvalue()


def results_page(user):
    title("Results","Review individual answers and update scores")
    attempts=[x for x in teacher_attempts(user["id"]) if x["status"]=="submitted"]
    if not attempts: st.info("No submitted results."); return
    labels={f"{a['student']} · {a['quiz']} · {a['score']}/{a['max_score']}":a for a in attempts}; chosen=labels[st.selectbox("Student result",labels)]
    answers=json.loads(chosen["answers_json"] or "{}"); st.json(answers)
    score=st.number_input("Reviewed score",0.0,float(chosen["max_score"] or 100),float(chosen["score"] or 0))
    if st.button("Save reviewed result"): run("UPDATE attempts SET score=? WHERE id=?",(score,chosen["id"])); st.success("Reviewed result saved.")


def resources_page(user):
    title("Resources","Share files, videos, or website links with a class")
    classes=rows("SELECT * FROM classes WHERE teacher_id=?",(user["id"],)); labels={c["name"]:c["id"] for c in classes}
    if not labels: st.info("Create a class first."); return
    kind=st.radio("Resource type",["Upload file","Website/video link"],horizontal=True); cls=st.selectbox("Share with class",labels)
    if kind=="Upload file":
        file=st.file_uploader("PDF, image, Word, or video",type=["pdf","png","jpg","jpeg","doc","docx","mp4","mov"])
        if file and st.button("Upload and share"):
            path=UPLOADS/f"{int(time.time())}-{file.name}"; path.write_bytes(file.getvalue()); run("INSERT INTO resources(teacher_id,class_id,title,kind,location,created_at) VALUES(?,?,?,?,?,?)",(user["id"],labels[cls],file.name,"file",str(path),now_iso())); st.success("Shared.")
    else:
        name=st.text_input("Title"); url=st.text_input("Website or video URL")
        if st.button("Share link"): run("INSERT INTO resources(teacher_id,class_id,title,kind,location,created_at) VALUES(?,?,?,?,?,?)",(user["id"],labels[cls],name,"link",url,now_iso())); st.success("Shared.")
    st.dataframe(pd.DataFrame(rows("SELECT r.title,r.kind,r.location,c.name class_name,r.created_at FROM resources r JOIN classes c ON c.id=r.class_id WHERE r.teacher_id=?",(user["id"],))),use_container_width=True,hide_index=True)


def student_app():
    student=st.session_state.student; class_id=st.session_state.class_id
    with st.sidebar: st.title("Q · Student"); st.write(student["name"]); st.button("Sign out",on_click=logout)
    quiz_id=st.session_state.get("direct_quiz"); quizzes=rows("SELECT * FROM quizzes WHERE class_id=? AND status='Live' ORDER BY id DESC",(class_id,))
    quiz=next((q for q in quizzes if q["id"]==quiz_id),quizzes[0] if quizzes else None)
    resources=rows("SELECT * FROM resources WHERE class_id=? ORDER BY id DESC",(class_id,))
    if not quiz:
        title("Class resources","No live quiz is available."); show_resources(resources); return
    attempts=rows("SELECT * FROM attempts WHERE quiz_id=? AND student_id=? ORDER BY id DESC",(quiz["id"],student["id"]))
    submitted=next((a for a in attempts if a["status"]=="submitted"),None)
    if submitted:
        title("Quiz submitted"); st.success(f"Score: {submitted['score']}/{submitted['max_score']}"); st.json(json.loads(submitted["answers_json"] or "{}")); return
    attempt=next((a for a in attempts if a["status"]=="in_progress"),None)
    if not attempt:
        aid=run("INSERT INTO attempts(quiz_id,student_id,started_at,last_seen) VALUES(?,?,?,?)",(quiz["id"],student["id"],now_iso(),now_iso())); attempt=rows("SELECT * FROM attempts WHERE id=?",(aid,))[0]
    previous=datetime.fromisoformat(attempt["last_seen"] or attempt["started_at"]); gap=int((datetime.now(timezone.utc)-previous).total_seconds())
    if gap>=15: run("INSERT INTO activity_events(attempt_id,event_type,started_at,ended_at,duration_seconds) VALUES(?,?,?,?,?)",(attempt["id"],"Quiz inactive",previous.isoformat(),now_iso(),gap))
    run("UPDATE attempts SET last_seen=? WHERE id=?",(now_iso(),attempt["id"])); st_autorefresh(interval=3000,key=f"student_ping_{attempt['id']}")
    title(quiz["title"],f"Protected quiz · {quiz['time_limit']} minutes · Activity is monitored")
    questions=rows("SELECT * FROM questions WHERE quiz_id=?",(quiz["id"],)); answers={}
    with st.form("quiz_answers"):
        for index,q in enumerate(questions,1):
            st.markdown(f"**{index}. {q['prompt']}** · {q['points']} pt")
            options=json.loads(q["options_json"] or "[]")
            answers[str(q["id"])]=st.radio("Choose an answer",options,key=f"a{q['id']}",label_visibility="collapsed") if options else st.text_area("Your answer",key=f"a{q['id']}")
        ready=st.checkbox("I am ready to submit and understand my answers cannot be changed.")
        if st.form_submit_button("Submit quiz",disabled=not ready): submit_attempt(attempt,questions,answers)
    show_resources(resources)


def submit_attempt(attempt,questions,answers):
    score=0; maximum=0
    for q in questions:
        maximum+=q["points"]
        if str(answers.get(str(q["id"]),"")).strip().lower()==str(q["correct_answer"] or "").strip().lower(): score+=q["points"]
    run("UPDATE attempts SET status='submitted',submitted_at=?,score=?,max_score=?,answers_json=? WHERE id=?",(now_iso(),score,maximum,json.dumps(answers),attempt["id"])); st.rerun()


def show_resources(resources):
    st.subheader("Class resources")
    for item in resources:
        if item["kind"]=="link": st.link_button(item["title"],item["location"])
        elif Path(item["location"]).exists(): st.download_button(item["title"],Path(item["location"]).read_bytes(),file_name=Path(item["location"]).name,key=f"r{item['id']}")


def admin_app():
    with st.sidebar: st.title("Q · Admin"); st.button("Sign out",on_click=logout)
    title("Administration","All teacher capabilities plus account management")
    users=rows("SELECT id,role,name,email,active FROM users ORDER BY id"); st.dataframe(pd.DataFrame(users),use_container_width=True,hide_index=True)
    selected=st.selectbox("Account",{f"{u['name']} · {u['email']}":u["id"] for u in users})
    if st.button("Toggle account status"): run("UPDATE users SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(selected,)); st.rerun()


init_db()
if "role" not in st.session_state: login()
elif st.session_state.role=="teacher": teacher_app()
elif st.session_state.role=="student": student_app()
else: admin_app()
