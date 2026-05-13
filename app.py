from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from datetime import date
from lang import LANG   # 🔥 NEW

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = "sharmsetu_secret"

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect("sharmsetu.db", timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS supervisor(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS workers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            work_type TEXT NOT NULL,
            wage_per_day INTEGER NOT NULL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER,
            date TEXT,
            status TEXT,
            UNIQUE(worker_id,date)
        )''')

        conn.commit()

init_db()

# ---------------- LANGUAGE ROUTE ----------------
@app.route("/setlang/<language>")
def set_language(language):
    session["lang"] = language
    return redirect(request.referrer or '/')

# ---------------- TEST ----------------
@app.route('/test')
def test():
    return "Test Working"

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    lang_code = session.get("lang", "en")
    lang = LANG[lang_code]

    if request.method == 'POST':
        try:
            username = request.form['username'].strip()
            password = request.form['password'].strip()

            with get_db() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO supervisor(username,password) VALUES(?,?)",
                          (username,password))
                conn.commit()

            flash(lang["account_created"])
            return redirect('/')

        except sqlite3.IntegrityError:
            return lang["username_exists"]

        except Exception as e:
            return f"Error: {e}"

    return render_template('register.html', lang=lang)

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    lang_code = session.get("lang", "en")
    lang = LANG[lang_code]

    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')

        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM supervisor WHERE username=? AND password=?", (u, p))
            user = c.fetchone()

        if user:
            session['user'] = u
            return redirect('/dashboard')
        else:
            flash(lang["invalid_login"])

    return render_template('login.html', lang=lang)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    lang_code = session.get("lang", "en")
    lang = LANG[lang_code]

    today = str(date.today())

    with get_db() as conn:
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM workers")
        total_workers = c.fetchone()[0]

        c.execute("""
            SELECT COUNT(*) FROM attendance
            WHERE date=? AND status='Present'
        """, (today,))
        present_today = c.fetchone()[0]

        c.execute("""
            SELECT SUM(w.wage_per_day)
            FROM workers w
            JOIN attendance a ON w.id = a.worker_id
            WHERE a.date=? AND a.status='Present'
        """, (today,))
        wage_today = c.fetchone()[0]
        if wage_today is None:
            wage_today = 0

        c.execute("""
            SELECT w.name, w.work_type,
                   COALESCE(a.status,'Absent') as status,
                   CASE 
                       WHEN a.status='Present' THEN w.wage_per_day
                       ELSE 0
                   END as wage
            FROM workers w
            LEFT JOIN attendance a
            ON w.id = a.worker_id AND a.date=?
        """, (today,))
        table_data = c.fetchall()

    absent_today = total_workers - present_today

    return render_template(
        'dashboard.html',
        total_workers=total_workers,
        present_today=present_today,
        absent_today=absent_today,
        wage_today=wage_today,
        table_data=table_data,
        username=session['user'],
        lang=lang   # 🔥 IMPORTANT
    )

# ---------------- ADD WORKER ----------------
@app.route('/add_worker', methods=['GET', 'POST'])
def add_worker():
    if 'user' not in session:
        return redirect('/')

    lang_code = session.get("lang", "en")
    lang = LANG[lang_code]

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        work_type = request.form.get('work_type')
        wage = request.form.get('wage')

        if not name or not phone or not work_type or not wage:
            flash(lang["all_fields"])
            return redirect('/add_worker')

        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO workers (name, phone, work_type, wage_per_day)
                    VALUES (?, ?, ?, ?)
                """, (name, phone, work_type, int(wage)))
                conn.commit()

            flash(lang["worker_added"])
            return redirect('/dashboard')

        except sqlite3.IntegrityError:
            flash(lang["phone_exists"])
            return redirect('/add_worker')

    return render_template('add_worker.html', lang=lang)

# ---------------- ATTENDANCE ----------------
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user' not in session:
        return redirect('/')

    lang_code = session.get("lang", "en")
    lang = LANG[lang_code]

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM workers")
        workers = c.fetchall()

    if request.method == 'POST':
        wid = request.form.get('worker_id')
        dt = request.form.get('date')
        st = request.form.get('status')

        if not wid or not dt or not st:
            flash(lang["all_fields"])
            return redirect('/attendance')

        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO attendance(worker_id,date,status)
                VALUES(?,?,?)
                ON CONFLICT(worker_id,date)
                DO UPDATE SET status=excluded.status
            ''', (wid, dt, st))
            conn.commit()

        flash(lang["attendance_saved"])
        return redirect('/attendance')

    return render_template('attendance.html', workers=workers, lang=lang)

# ---------------- REPORT ----------------
@app.route('/report')
def report():
    if 'user' not in session:
        return redirect('/')

    lang_code = session.get("lang", "en")
    lang = LANG[lang_code]

    with get_db() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT w.name,
                   COUNT(CASE WHEN a.status='Present' THEN 1 END) as present_days,
                   w.wage_per_day,
                   COUNT(CASE WHEN a.status='Present' THEN 1 END) * w.wage_per_day as total_wage
            FROM workers w
            LEFT JOIN attendance a ON w.id = a.worker_id
            GROUP BY w.id
        ''')
        data = c.fetchall()

    return render_template('report.html', data=data, lang=lang)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)