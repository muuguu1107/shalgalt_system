from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

import os
import random
import pandas as pd
from datetime import datetime


app = Flask(__name__)

# =========================================================
# Тохиргоо
# =========================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "shalgalt-system-2026-secret"
)

# Админы нууц үг
# Render дээр ADMIN_PASSWORD environment variable болгож
# өөрийн нууц үгийг тохируулж болно.
ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)

# Excel файл
EXCEL_FILE = "results.xlsx"

# Шалгалтын тохиргоо
QUESTION_COUNT = 10
EXAM_MINUTES = 10
PASS_SCORE = 8


# =========================================================
# Шалгалтын төлөв
# =========================================================
#
# False = хаалттай
# True  = нээлттэй
#
# Анх ажиллахдаа хаалттай байна.
# =========================================================

EXAM_OPEN = False


# =========================================================
# Асуултын файл
# =========================================================

EXAM_FILES = {
    "ААД": os.path.join("ААД", "questions.txt"),
    "Нарядын систем": os.path.join("Нарядын систем", "questions.txt")
}


# =========================================================
# Questions.txt унших
# =========================================================

def load_questions(filepath):

    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8-sig") as f:
        text = f.read()

    # Windows newline-ийг нэг хэлбэрт оруулах
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Хоосон мөрөөр асуултуудыг салгана
    blocks = []

    current = []

    for line in text.split("\n"):

        line = line.strip()

        if line:
            current.append(line)

        else:
            if current:
                blocks.append(current)
                current = []

    if current:
        blocks.append(current)

    questions = []

    for block in blocks:

        question_text = ""
        options = {}
        correct_answer = None

        for line in block:

            # Зөв хариулт
            lower_line = line.lower()

            if (
                lower_line.startswith("зөв хариулт")
                or lower_line.startswith("зөв хариу")
            ):
                if ":" in line:
                    correct_answer = (
                        line.split(":", 1)[1]
                        .strip()
                        .upper()
                    )
                continue

            # A)
            # A.
            # A -
            if len(line) >= 2 and line[0].upper() in "ABCD":

                letter = line[0].upper()

                if (
                    line[1] in [")", ".", ":"]
                    or line[1] == "-"
                ):
                    answer_text = line[2:].strip()

                    if answer_text:
                        options[letter] = answer_text
                        continue

            # Асуултын текст
            if not question_text:
                question_text = line

            else:
                question_text += " " + line

        # Хамгийн багадаа 2 сонголттой бол асуулт гэж үзнэ
        if (
            question_text
            and len(options) >= 2
            and correct_answer
        ):

            questions.append({
                "question": question_text,
                "options": options,
                "correct": correct_answer
            })

    return questions


# =========================================================
# Шалгалтын бүх асуултыг авах
# =========================================================

def get_exam_questions(exam_type):

    filepath = EXAM_FILES.get(exam_type)

    if not filepath:
        return []

    return load_questions(filepath)


# =========================================================
# Нүүр хуудас
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html",
        exam_open=EXAM_OPEN
    )


# =========================================================
# Шалгалтын төрөл сонгох
# =========================================================

@app.route("/select_exam", methods=["POST"])
def select_exam():

    if not EXAM_OPEN:
        return render_template(
            "error.html",
            message="Шалгалт одоогоор хаалттай байна."
        )

    exam_type = request.form.get("exam_type")

    if exam_type not in EXAM_FILES:
        return render_template(
            "error.html",
            message="Шалгалтын төрөл буруу байна."
        )

    session["exam_type"] = exam_type

    return redirect(url_for("info"))


# =========================================================
# Мэдээлэл оруулах
# =========================================================

@app.route("/info")
def info():

    if not EXAM_OPEN:
        return render_template(
            "error.html",
            message="Шалгалт одоогоор хаалттай байна."
        )

    exam_type = session.get("exam_type")

    if not exam_type:
        return redirect(url_for("index"))

    return render_template(
        "info.html",
        exam_type=exam_type
    )


# =========================================================
# Шалгалт эхлүүлэх
# =========================================================

@app.route("/start", methods=["POST"])
def start():

    if not EXAM_OPEN:
        return render_template(
            "error.html",
            message="Шалгалт одоогоор хаалттай байна."
        )

    surname = request.form.get("surname", "").strip()
    position = request.form.get("position", "").strip()

    if not surname:
        return render_template(
            "error.html",
            message="Овог нэрээ оруулна уу."
        )

    if not position:
        return render_template(
            "error.html",
            message="Албан тушаалаа оруулна уу."
        )

    exam_type = session.get("exam_type")

    if not exam_type:
        return redirect(url_for("index"))

    all_questions = get_exam_questions(exam_type)

    if len(all_questions) < QUESTION_COUNT:
        return render_template(
            "error.html",
            message=(
                f"{exam_type} шалгалтын асуултын тоо "
                f"{QUESTION_COUNT}-аас бага байна."
            )
        )

    # Санамсаргүй 10 асуулт
    selected_questions = random.sample(
        all_questions,
        QUESTION_COUNT
    )

    # Session-д зөвхөн асуултын мэдээллийг хадгална
    session["questions"] = selected_questions

    session["surname"] = surname
    session["position"] = position

    session["exam_started"] = True

    return redirect(url_for("exam"))


# =========================================================
# Шалгалтын хуудас
# =========================================================

@app.route("/exam")
def exam():

    if not EXAM_OPEN:
        return render_template(
            "error.html",
            message="Шалгалт одоогоор хаалттай байна."
        )

    if not session.get("exam_started"):
        return redirect(url_for("index"))

    questions = session.get("questions")

    if not questions:
        return redirect(url_for("index"))

    return render_template(
        "exam.html",
        questions=questions,
        exam_minutes=EXAM_MINUTES,
        surname=session.get("surname"),
        position=session.get("position"),
        exam_type=session.get("exam_type")
    )


# =========================================================
# Шалгалт дуусгах
# =========================================================

@app.route("/submit", methods=["POST"])
def submit():

    if not EXAM_OPEN:
        return render_template(
            "error.html",
            message="Шалгалт хаалттай болсон байна."
        )

    if not session.get("exam_started"):
        return redirect(url_for("index"))

    questions = session.get("questions", [])

    score = 0

    for i, question in enumerate(questions):

        answer = request.form.get(
            f"question_{i}"
        )

        if answer:
            answer = answer.upper()

        if answer == question["correct"]:
            score += 1

    total = len(questions)

    percentage = 0

    if total > 0:
        percentage = round(
            score / total * 100,
            1
        )

    if score >= PASS_SCORE:
        status = "ТЭНЦСЭН"
    else:
        status = "ТЭНЦЭЭГҮЙ"

    # =====================================================
    # Excel-д хадгалах
    # =====================================================

    new_row = {
        "Огноо": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "Овог нэр": session.get(
            "surname",
            ""
        ),
        "Албан тушаал": session.get(
            "position",
            ""
        ),
        "Шалгалтын төрөл": session.get(
            "exam_type",
            ""
        ),
        "Авсан оноо": score,
        "Нийт оноо": total
    }

    try:

        if os.path.exists(EXCEL_FILE):

            df = pd.read_excel(
                EXCEL_FILE
            )

            df = pd.concat(
                [
                    df,
                    pd.DataFrame([new_row])
                ],
                ignore_index=True
            )

        else:

            df = pd.DataFrame(
                [new_row]
            )

        df.to_excel(
            EXCEL_FILE,
            index=False
        )

    except Exception as e:

        print(
            "Excel хадгалалтын алдаа:",
            e
        )

    # Session цэвэрлэх
    session.pop("questions", None)
    session.pop("exam_started", None)

    return render_template(
        "result.html",
        score=score,
        total=total,
        percentage=percentage,
        status=status
    )


# =========================================================
# АДМИН LOGIN
# =========================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    global EXAM_OPEN

    # -----------------------------------------------------
    # Нэвтрэх
    # -----------------------------------------------------

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if password == ADMIN_PASSWORD:

            session["admin"] = True

            return redirect(
                url_for("admin")
            )

        return render_template(
            "admin.html",
            logged_in=False,
            error="Нууц үг буруу байна.",
            exam_open=EXAM_OPEN
        )

    # -----------------------------------------------------
    # Login хийсэн эсэх
    # -----------------------------------------------------

    if not session.get("admin"):

        return render_template(
            "admin.html",
            logged_in=False,
            error=None,
            exam_open=EXAM_OPEN
        )

    return render_template(
        "admin.html",
        logged_in=True,
        error=None,
        exam_open=EXAM_OPEN
    )


# =========================================================
# ШАЛГАЛТ НЭЭХ
# =========================================================

@app.route("/admin/open", methods=["POST"])
def admin_open():

    global EXAM_OPEN

    if not session.get("admin"):
        return redirect(
            url_for("admin")
        )

    EXAM_OPEN = True

    return redirect(
        url_for("admin")
    )


# =========================================================
# ШАЛГАЛТ ХААХ
# =========================================================

@app.route("/admin/close", methods=["POST"])
def admin_close():

    global EXAM_OPEN

    if not session.get("admin"):
        return redirect(
            url_for("admin")
        )

    EXAM_OPEN = False

    # Хаах үед тухайн session дээрх шалгалтыг
    # үргэлжлүүлэх боломжгүй болгоно.
    session.pop("questions", None)
    session.pop("exam_started", None)

    return redirect(
        url_for("admin")
    )


# =========================================================
# АДМИН ГАРАХ
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin", None)

    return redirect(
        url_for("admin")
    )


# =========================================================
# Error
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "error.html",
        message="Хуудас олдсонгүй."
    ), 404


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )