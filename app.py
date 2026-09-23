from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timezone
from functools import wraps
import os
import random
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

# =========================
# Тохиргоо
# =========================
QUESTION_COUNT = 10
EXAM_MINUTES = 10
PASS_SCORE = 8

EXAM_FILES = {
    "ААД": os.path.join("ААД", "questions.txt"),
    "Нарядын систем": os.path.join("Нарядын систем", "questions.txt"),
}

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_SECRET_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


# =========================
# Асуулт унших
# =========================
QUESTION_RE = re.compile(r"^\s*(?:\d+\s*[\.\)]\s*)?(.+?)\s*$")
OPTION_RE = re.compile(r"^\s*([ABCDАБСД])\s*[\)\.\:\-]\s*(.+?)\s*$", re.I)
CORRECT_RE = re.compile(r"^\s*зөв\s*хариулт\s*:\s*([ABCDАБСД])\s*$", re.I)


def normalize_letter(letter):
    mapping = {"А": "A", "Б": "B", "С": "C", "Д": "D"}
    return mapping.get(letter.upper(), letter.upper())


def parse_questions(filepath):
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = [line.strip() for line in f.readlines()]

    # Илүүдэл хоосон мөрийг цэвэрлэх боловч асуултын блок салгахыг хадгална
    blocks = []
    current = []

    for line in lines:
        if line:
            current.append(line)
        elif current:
            blocks.append(current)
            current = []

    if current:
        blocks.append(current)

    questions = []

    for block in blocks:
        question_text_parts = []
        options = {}
        correct = None

        for line in block:
            m_correct = CORRECT_RE.match(line)
            if m_correct:
                correct = normalize_letter(m_correct.group(1))
                continue

            m_option = OPTION_RE.match(line)
            if m_option:
                letter = normalize_letter(m_option.group(1))
                options[letter] = m_option.group(2).strip()
                continue

            # Асуултын дугаар (205. / 205) -ийг авч цэвэрлэнэ
            cleaned = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", line)
            if cleaned:
                question_text_parts.append(cleaned)

        if question_text_parts and len(options) in (3, 4) and correct in options:
            questions.append({
                "question": " ".join(question_text_parts).strip(),
                "options": options,
                "correct": correct,
            })

    return questions


def get_questions(exam_type):
    filepath = EXAM_FILES.get(exam_type)
    if not filepath:
        return []
    return parse_questions(filepath)


# =========================
# Supabase
# =========================
def require_supabase():
    if supabase is None:
        raise RuntimeError(
            "SUPABASE_URL болон SUPABASE_SECRET_KEY Environment Variable тохируулаагүй байна."
        )


def get_exam_open():
    require_supabase()
    result = supabase.table("exam_settings").select("is_open").eq("id", 1).single().execute()
    return bool(result.data["is_open"])


def set_exam_open(value):
    require_supabase()
    supabase.table("exam_settings").update({
        "is_open": bool(value),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", 1).execute()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin"))
        return view(*args, **kwargs)
    return wrapped


# =========================
# Нүүр
# =========================
@app.route("/")
def index():
    try:
        exam_open = get_exam_open()
    except Exception as e:
        return render_template("error.html",
                               message=f"Системийн тохиргооны алдаа: {e}")
    return render_template("index.html", exam_open=exam_open)


# =========================
# Шалгалтын төрөл сонгох
# =========================
@app.post("/select-exam")
def select_exam():
    try:
        if not get_exam_open():
            return render_template("closed.html")

        exam_type = request.form.get("exam_type", "").strip()
        if exam_type not in EXAM_FILES:
            return render_template("error.html", message="Шалгалтын төрөл буруу байна.")

        questions = get_questions(exam_type)
        if len(questions) < QUESTION_COUNT:
            return render_template(
                "error.html",
                message=f"{exam_type} шалгалтад {QUESTION_COUNT}-аас бага асуулт байна. Одоогийн асуулт: {len(questions)}"
            )

        session["exam_type"] = exam_type
        return redirect(url_for("info"))
    except Exception as e:
        return render_template("error.html", message=str(e))


# =========================
# Мэдээлэл
# =========================
@app.route("/info")
def info():
    try:
        if not get_exam_open():
            return render_template("closed.html")

        exam_type = session.get("exam_type")
        if not exam_type:
            return redirect(url_for("index"))

        return render_template(
            "info.html",
            exam_type=exam_type,
            question_count=QUESTION_COUNT,
            exam_minutes=EXAM_MINUTES,
            pass_score=PASS_SCORE,
        )
    except Exception as e:
        return render_template("error.html", message=str(e))


# =========================
# Шалгалт эхлүүлэх
# =========================
@app.post("/start")
def start():
    try:
        if not get_exam_open():
            return render_template("closed.html")

        exam_type = session.get("exam_type")
        surname = request.form.get("surname", "").strip()
        position = request.form.get("position", "").strip()

        if not exam_type:
            return redirect(url_for("index"))
        if not surname or not position:
            return render_template(
                "error.html",
                message="Овог нэр болон албан тушаалаа бүрэн оруулна уу."
            )

        all_questions = get_questions(exam_type)
        if len(all_questions) < QUESTION_COUNT:
            return render_template(
                "error.html",
                message=f"Шалгалтад {QUESTION_COUNT} асуулт шаардлагатай."
            )

        selected = random.sample(all_questions, QUESTION_COUNT)

        # Зөв хариуг browser/session-д ил гаргахгүй.
        public_questions = []
        for q in selected:
            public_questions.append({
                "question": q["question"],
                "options": q["options"],
                "correct": q["correct"],  # session server-side signed cookie-д байна; production-д илүү secure storage ашиглаж болно
            })

        session["surname"] = surname
        session["position"] = position
        session["questions"] = public_questions
        session["started_at"] = datetime.now(timezone.utc).timestamp()
        session["exam_started"] = True

        return redirect(url_for("exam"))
    except Exception as e:
        return render_template("error.html", message=str(e))


# =========================
# Шалгалт
# =========================
@app.route("/exam")
def exam():
    try:
        if not get_exam_open():
            return render_template("closed.html")

        if not session.get("exam_started") or not session.get("questions"):
            return redirect(url_for("index"))

        elapsed = datetime.now(timezone.utc).timestamp() - float(session.get("started_at", 0))
        remaining = max(0, EXAM_MINUTES * 60 - int(elapsed))

        return render_template(
            "exam.html",
            questions=session["questions"],
            remaining_seconds=remaining,
            exam_type=session.get("exam_type"),
            surname=session.get("surname"),
            position=session.get("position"),
        )
    except Exception as e:
        return render_template("error.html", message=str(e))


# =========================
# Илгээх
# =========================
@app.post("/submit")
def submit():
    try:
        if not get_exam_open():
            return render_template("closed.html")

        if not session.get("exam_started"):
            return redirect(url_for("index"))

        questions = session.get("questions", [])
        if not questions:
            return redirect(url_for("index"))

        started_at = float(session.get("started_at", 0))
        elapsed = datetime.now(timezone.utc).timestamp() - started_at

        score = 0
        for i, q in enumerate(questions):
            answer = normalize_letter(request.form.get(f"question_{i}", ""))
            if answer == q["correct"]:
                score += 1

        total = len(questions)
        percent = round(score / total * 100, 1) if total else 0
        result = "ТЭНЦСЭН" if score >= PASS_SCORE else "ТЭНЦЭЭГҮЙ"

        # Хугацаа дууссан бол мөн адил автоматаар дүнг хадгална.
        timed_out = elapsed > EXAM_MINUTES * 60 + 5

        require_supabase()
        supabase.table("exam_results").insert({
            "exam_date": datetime.now(timezone.utc).isoformat(),
            "exam_type": session.get("exam_type"),
            "surname": session.get("surname"),
            "position": session.get("position"),
            "score": score,
            "total_score": total,
            "percentage": percent,
            "result": result,
        }).execute()

        session.clear()

        return render_template(
            "result.html",
            score=score,
            total=total,
            percentage=percent,
            result=result,
            timed_out=timed_out,
        )
    except Exception as e:
        return render_template("error.html", message=f"Үр дүн хадгалах үед алдаа гарлаа: {e}")


# =========================
# ADMIN
# =========================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password", "")
        if not ADMIN_PASSWORD:
            return render_template(
                "admin.html",
                logged_in=False,
                error="Render Environment дээр ADMIN_PASSWORD тохируулаагүй байна."
            )

        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))

        return render_template(
            "admin.html",
            logged_in=False,
            error="Нууц үг буруу байна."
        )

    if not session.get("admin_logged_in"):
        return render_template(
            "admin.html",
            logged_in=False,
            error=None
        )

    try:
        exam_open = get_exam_open()
        return render_template(
            "admin.html",
            logged_in=True,
            exam_open=exam_open,
            error=None
        )
    except Exception as e:
        return render_template(
            "admin.html",
            logged_in=True,
            exam_open=False,
            error=str(e)
        )


@app.post("/admin/open")
@admin_required
def admin_open():
    try:
        set_exam_open(True)
        return redirect(url_for("admin"))
    except Exception as e:
        return render_template("error.html", message=str(e))


@app.post("/admin/close")
@admin_required
def admin_close():
    try:
        set_exam_open(False)
        return redirect(url_for("admin"))
    except Exception as e:
        return render_template("error.html", message=str(e))


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", message="Хуудас олдсонгүй."), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
