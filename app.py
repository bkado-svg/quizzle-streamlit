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

st.set_page_config(page_title="Quizzle", page_icon="Q", layout="wide")


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
    for role, name, email, password in [("admin", "Quizzle Administrator", "admin@quizzle.app", "Admin123!"), ("teacher", "Demo Teacher", "teacher@quizzle.app", "Teacher123!")]:
        con.execute("INSERT OR IGNORE INTO users(role,name,email,password_hash) VALUES(?,?,?,?)", (role, name, email, password_hash(password)))
    con.commit(); con.close()


def rows(sql, params=()):
    con = db(); result = [dict(row) for row in con.execute(sql, params).fetchall()]; con.close(); return result


def run(sql, params=()):
    con = db(); cursor = con.execute(sql, params); con.commit(); value = cursor.lastrowid; con.close(); return value


def code(prefix="QZ"):
    return f"{prefix}{int(time.time()*1000)%1000000:06d}"


def title(text, caption=None):
    st.markdown(f"## {text}")
    if caption: st.caption(caption)


def logout():
    st.session_state.clear(); st.rerun()


def login():
    st.markdown("<h1 style='text-align:center'>Q · Quizzle</h1><p style='text-align:center;color:#777'>Teach · Assess · Improve</p>", unsafe_allow_html=True)
    teacher, student, admin = st.tabs(["Teacher", "Student", "Admin"])
    with teacher:
        with st.form("teacher_login"):
            email = st.text_input("Email", key="te"); password = st.text_input("Password", type="password", key="tp")
            if st.form_submit_button("Sign in", use_container_width=True): authenticate(email, password, "teacher")
        with st.expander("Create teacher account"):
            with st.form("register"):
                name=st.text_input("Full name"); email=st.text_input("Institutional email"); password=st.text_input("Create password",type="password")
                university_type=st.selectbox("University type",["Federal","State","Private"]); university=st.text_input("University"); faculty=st.text_input("Faculty"); department=st.text_input("Department")
                if st.form_submit_button("Create account"):
                    try: run("INSERT INTO users(role,name,email,password_hash) VALUES('teacher',?,?,?)",(name,email.lower(),password_hash(password))); st.success("Account created. Please sign in.")
                    except sqlite3.IntegrityError: st.error("That email is already registered.")
    with student:
        with st.form("student_login"):
            join=st.text_input("Class or quiz code").strip().upper(); number=st.text_input("Student number").strip(); name=st.text_input("Full name")
            if st.form_submit_button("Open class",use_container_width=True): student_signin(join,number,name)
    with admin:
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
        st.title("Q · Quizzle"); page=st.radio("Workspace",["Overview","Classes","My quizzes","Monitoring","Reports","Results","Resources"]); st.caption(user["name"]); st.button("Sign out",on_click=logout)
    if page=="Overview": teacher_overview(user)
    elif page=="Classes": classes_page(user)
    elif page=="My quizzes": quizzes_page(user)
    elif page=="Monitoring": monitoring_page(user)
    elif page=="Reports": reports_page(user)
    elif page=="Results": results_page(user)
    else: resources_page(user)


def teacher_overview(user):
    title("Overview","Live summary of teaching activity")
    cs=rows("SELECT * FROM classes WHERE teacher_id=?",(user["id"],)); qs=rows("SELECT * FROM quizzes WHERE teacher_id=?",(user["id"],)); reports=teacher_attempts(user["id"])
    a,b,c,d=st.columns(4); a.metric("Classes",len(cs)); b.metric("Quizzes",len(qs)); c.metric("Submissions",sum(x["status"]=="submitted" for x in reports)); d.metric("Activity alerts",sum(x["alert_count"] for x in reports))
    st.subheader("Recent activity"); st.dataframe(pd.DataFrame(reports[:10]) if reports else pd.DataFrame(columns=["student","quiz","status"]),use_container_width=True,hide_index=True)


def classes_page(user):
    title("Classes","Levels and academic sessions organise courses")
    with st.expander("Create class",expanded=not rows("SELECT id FROM classes WHERE teacher_id=?",(user["id"],))):
        with st.form("new_class"):
            name=st.text_input("Class name"); level=st.selectbox("Level",["100","200","300","400","500","Postgraduate"]); session=st.text_input("Session",f"{datetime.now().year-1}/{str(datetime.now().year)[-2:]}"); course=st.text_input("Course")
            if st.form_submit_button("Create class"):
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
